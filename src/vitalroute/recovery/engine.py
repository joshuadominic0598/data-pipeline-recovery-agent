"""Durable recovery state machine, one Spark worker, approval bound to tested artifacts."""

import json
import os
import queue
import shutil
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ..agent.investigator import investigate
from ..agent.policy import RECIPES, patch, proposal_digest, verify_patch
from ..config import TEMPLATE
from ..integrations.email import flush, notify
from ..integrations.releases import deploy_release
from ..pipeline.errors import PipelineFailure
from ..pipeline.executor import execute, spark_session
from ..pipeline.source import input_digest, seed, sha
from .store import now

ACTIVE = {"queued", "running", "investigating", "testing", "approved", "applying", "verifying"}

class Engine:
    def __init__(self, store):
        self.store = store
        self.queue = queue.Queue()
        self.spark = None
        self.stop = threading.Event()
        self.thread = None
        self.lockfile = None

    def start(self):
        # SQLite is durable; the filesystem lock prevents multiple Spark workers against one state dir.
        import fcntl

        self.lockfile = (self.store.root / "worker.lock").open("w")
        fcntl.flock(self.lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for mail in self.store.emails():
            if mail["status"] == "sending":
                self.store.email_status(
                    mail["id"],
                    "delivery_unknown",
                    error="Worker restarted during send; inspect Gmail before retry",
                )
        for run in reversed(self.store.list()):
            if run["status"] in ACTIVE:
                self.store.event(
                    run["id"],
                    "checkpoint",
                    "Worker restarted · resume durable state",
                    previous_status=run["status"],
                )
                self.queue.put(run["id"])
        self.thread = threading.Thread(target=self.work, name="spark-recovery-worker", daemon=True)
        self.thread.start()

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=3)
        # Process shutdown releases the lease; Spark jobs are replayed from saved artifacts on restart.

    def trigger(self, scenario, day, mode=None, key=None):
        rid = "VR-" + uuid.uuid4().hex[:8].upper()
        run, created = self.store.create(
            {
                "id": rid,
                "date": day,
                "scenario": scenario,
                "status": "queued",
                "agent_mode": mode or os.getenv("AGENT_MODE", "ollama"),
                "stages": {},
                "attempts": 0,
            },
            key,
        )
        if created:
            self.store.event(
                rid,
                "trigger",
                "Daily cold-chain pipeline triggered",
                partition=day,
                scenario=scenario,
                trigger="schedule" if key and key.startswith("daily:") else "dashboard",
            )
            self.queue.put(rid)
        return run

    def work(self):
        last_schedule_check = 0
        while not self.stop.is_set():
            try:
                if time.monotonic() - last_schedule_check > 30:
                    self.schedule_tick()
                    flush(self.store)
                    last_schedule_check = time.monotonic()
                rid = self.queue.get(timeout=1)
            except queue.Empty:
                continue
            try:
                run = self.store.get(rid)
                if run["status"] not in ACTIVE:
                    continue
                if self.spark is None:
                    self.store.event(
                        rid, "runtime", "Starting local Apache Spark", master="local[2]", version="4.0.1"
                    )
                    self.spark = spark_session()
                self.process(rid)
            except Exception as exc:
                run = self.store.update(
                    rid, status="blocked", blocker=f"{type(exc).__name__}: {str(exc)[:800]}"
                )
                self.store.event(
                    rid, "blocked", "Recovery stopped · owner action needed", error=run["blocker"]
                )
                notify(self.store, run, "owner_action", run["blocker"])
            finally:
                flush(self.store)
                self.queue.task_done()

    def schedule_tick(self):
        if os.getenv("DAILY_SCHEDULE_ENABLED", "false").lower() != "true":
            return
        current = datetime.now(ZoneInfo("Asia/Kolkata"))
        if current.hour >= int(os.getenv("DAILY_HOUR_IST", "7")):
            self.trigger("healthy", current.date().isoformat(), key=f"daily:{current.date().isoformat()}")

    def emitter(self, rid, phase):
        def emit(kind, title, **body):
            self.store.event(rid, kind, title, phase=phase, **body)
            if phase != "sandbox" and kind in {"stage_start", "stage_done"}:
                run = self.store.get(rid)
                stages = dict(run["stages"])
                stages[body["stage"]] = "running" if kind == "stage_start" else "passed"
                self.store.update(rid, stages=stages)

        return emit

    def process(self, rid):
        run, root, baseline = self._prepare_run(rid)
        if not run.get("failure") and self._run_initial_pipeline(rid, root, baseline):
            return
        run = self.store.get(rid)
        if not run.get("proposal"):
            run = self._prepare_proposal(rid, run, root)
        proposal = run["proposal"]
        candidate = self._verify_proposal(root, proposal)
        if not run.get("sandbox"):
            run = self._test_candidate(rid, root, candidate)
        if self._await_approval(rid, run, proposal):
            return
        self._apply_repair(rid, run, root, candidate)

    def _prepare_run(self, rid):
        run = self.store.get(rid)
        root = self.store.root / "runs" / rid
        root.mkdir(parents=True, exist_ok=True)
        seed(root, run["date"], run["scenario"], os.getenv("WEATHER_LIVE", "false").lower() == "true")
        baseline = root / "baseline.py"
        if not baseline.exists():
            shutil.copy2(TEMPLATE, baseline)
        return run, root, baseline

    def _run_initial_pipeline(self, rid, root, baseline):
        self.store.update(rid, status="running")
        try:
            report = execute(self.spark, root, baseline, root / "production", self.emitter(rid, "pipeline"))
            self.publish(root, report)
            self.store.update(rid, status="succeeded", report=report, finished=now())
            self.store.event(
                rid, "complete", "Healthy refresh · data product published", metrics=report["metrics"]
            )
            return True
        except PipelineFailure as exc:
            stages = dict(self.store.get(rid)["stages"])
            stages[exc.stage] = "failed"
            run = self.store.update(rid, status="investigating", failure=exc.document(), stages=stages)
            self.store.event(rid, "failure", "Pipeline stopped · recovery agent activated", **exc.document())
            notify(self.store, run, "pipeline_failed", str(exc))
            flush(self.store)
        return False

    def _prepare_proposal(self, rid, run, root):
        self.store.update(rid, status="investigating")
        recipe, rationale, metrics, observations = investigate(
            self.spark, root, run["failure"], self.emitter(rid, "agent"), run["agent_mode"]
        )
        code, diff = patch(recipe)
        candidate = root / "candidate.py"
        candidate.write_text(code)
        inputs = input_digest(root)
        spec = RECIPES[recipe]
        proposal = {
            "recipe": recipe,
            "label": spec["label"],
            "cause": spec["cause"],
            "rationale": rationale,
            "impact": spec["impact"],
            "requires_approval": spec["approval"],
            "diff": diff,
            "input_digest": inputs,
            "code_sha256": sha(candidate),
            "digest": proposal_digest(code, inputs),
            "observations": observations,
        }
        run = self.store.update(rid, status="testing", proposal=proposal, agent_metrics=metrics)
        self.store.event(
            rid,
            "proposal",
            "Repair prepared · policy evaluated",
            proposal={k: v for k, v in proposal.items() if k != "observations"},
        )
        return run

    def _verify_proposal(self, root, proposal):
        candidate = root / "candidate.py"
        code = candidate.read_text()
        verify_patch(code, proposal["recipe"])
        if proposal_digest(code, input_digest(root)) != proposal["digest"]:
            raise ValueError("Inputs or candidate changed after proposal; approval/test invalidated")
        return candidate

    def _test_candidate(self, rid, root, candidate):
        self.store.update(rid, status="testing")
        self.store.event(
            rid,
            "sandbox",
            "Test candidate in isolated Spark output",
            isolation="Separate Parquet output paths; same immutable source snapshot; no production publication",
        )
        report = execute(self.spark, root, candidate, root / "sandbox", self.emitter(rid, "sandbox"))
        run = self.store.update(rid, sandbox=report)
        self.store.event(
            rid, "sandbox_passed", "Sandbox passed · all quality gates green", checks=report["checks"]
        )
        return run

    def _await_approval(self, rid, run, proposal):
        if proposal["requires_approval"] and not run.get("approval", {}).get("approved"):
            run = self.store.update(rid, status="awaiting_approval")
            self.store.event(
                rid,
                "approval",
                "Human approval required · checkpoint saved",
                impact=proposal["impact"],
                digest=proposal["digest"],
                note="A restart preserves this proposal, sandbox results and approval boundary.",
            )
            notify(self.store, run, "approval_required", proposal["impact"])
            return True
        return False

    def _apply_repair(self, rid, run, root, candidate):
        proposal = run["proposal"]

        if RECIPES[proposal["recipe"]]["approval"]:
            approval = run.get("approval", {})
            if not approval.get("approved") or approval.get("digest") != proposal["digest"]:
                raise ValueError("This repair requires approval of the exact tested proposal")
        else:
            self.store.event(
                rid,
                "policy",
                "Automatic repair allowed",
                reason="Evidence-eligible, reviewed runbook; no architecture, business-rule or dependency change",
            )
        self.store.update(rid, status="applying")
        if not run.get("deployment"):
            deployment = deploy_release(root, candidate, proposal)
            run = self.store.update(rid, deployment=deployment)
            self.store.event(rid, "deploy", "Tested code committed & deployed locally", **deployment)
        deployment = run["deployment"]
        if sha(Path(deployment["file"])) != proposal["code_sha256"]:
            raise ValueError("Deployed code differs from tested candidate")
        self.store.update(rid, status="verifying", attempts=run.get("attempts", 0) + 1)
        self.store.event(
            rid,
            "resume",
            "Resume failed task and downstream stages",
            from_stage=run["failure"]["stage"],
            note="Successful upstream Parquet checkpoints are reused.",
        )
        try:
            report = execute(
                self.spark,
                root,
                Path(deployment["file"]),
                root / "production",
                self.emitter(rid, "recovery"),
                resume_stage=run["failure"]["stage"],
            )
        except Exception:
            self.store.event(
                rid,
                "rollback",
                "Release failed verification · publication withheld",
                rollback="Previous published data pointer is unchanged. Failed release retained for investigation.",
            )
            raise
        self.publish(root, report)
        run = self.store.update(rid, status="recovered", report=report, finished=now())
        self.store.event(
            rid,
            "complete",
            "Recovery verified · data product published",
            metrics=report["metrics"],
            checks_passed=len(report["checks"]),
        )
        notify(
            self.store,
            run,
            "recovery_verified",
            f"All {len(report['checks'])} data-quality checks passed. {report['metrics']['rows']} accepted events; {report['metrics']['quarantined']} quarantined. Workflow resumed from {run['failure']['stage']}.",
        )

    def publish(self, root, report):
        target = self.store.root / "published.json"
        temp = self.store.root / "published.tmp"
        temp.write_text(
            json.dumps(
                {
                    "run_id": root.name,
                    "published": now(),
                    "output": report["output"],
                    "metrics": report["metrics"],
                },
                indent=2,
            )
        )
        temp.replace(target)
