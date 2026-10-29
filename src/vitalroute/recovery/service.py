"""Operator actions and incident views, independent of HTTP."""

from datetime import datetime

from ..config import SCENARIOS
from ..integrations.email import flush, notify

class RunNotFound(LookupError):
    pass

class RecoveryConflict(ValueError):
    pass

class RecoveryService:
    def __init__(self, store, engine):
        self.store = store
        self.engine = engine

    def get_run(self, run_id):
        try:
            return self.store.get(run_id)
        except KeyError as exc:
            raise RunNotFound("Run not found") from exc

    def detail(self, run_id):
        run = self.get_run(run_id)
        return {**run, "events": self.store.events(run_id), "emails": self.store.emails(run_id)}

    def events(self, run_id, after=0):
        self.get_run(run_id)
        return self.store.events(run_id, after)

    def decide(self, run_id, digest, approve, actor):
        self.get_run(run_id)
        try:
            run = self.store.decide(run_id, digest, approve, actor)
        except ValueError as exc:
            raise RecoveryConflict(str(exc)) from exc
        self.store.event(
            run_id,
            "human_decision",
            "Owner approved tested repair" if approve else "Owner rejected repair",
            actor=actor,
            digest=digest,
        )
        if approve:
            self.engine.queue.put(run_id)
        else:
            notify(
                self.store,
                run,
                "repair_rejected",
                "Owner rejected the candidate. No repair was deployed and the previous published data is unchanged.",
            )
            flush(self.store)
        return run

    def retry(self, run_id):
        run = self.get_run(run_id)
        if run["status"] != "blocked" or run.get("manual_retries", 0) >= 2:
            raise RecoveryConflict("Only blocked runs may be retried, at most twice")
        self.store.update(
            run_id, status="queued", manual_retries=run.get("manual_retries", 0) + 1, blocker=None
        )
        self.store.event(run_id, "operator", "Owner requested bounded retry")
        self.engine.queue.put(run_id)
        return {"queued": True}

    def evaluation(self):
        items = []
        for run in self.store.list():
            expected = SCENARIOS[run["scenario"]].get("cause")
            if not expected:
                continue
            actual = run.get("proposal", {}).get("cause")
            seconds = round(
                (
                    datetime.fromisoformat(run.get("finished", run["updated"]))
                    - datetime.fromisoformat(run["created"])
                ).total_seconds(),
                2,
            )
            items.append(
                {
                    "run_id": run["id"],
                    "scenario": run["scenario"],
                    "status": run["status"],
                    "expected_cause": expected,
                    "diagnosed_cause": actual,
                    "correct_diagnosis": actual == expected,
                    "verified_recovery": run["status"] == "recovered"
                    and all(c["passed"] for c in run.get("report", {}).get("checks", [])),
                    "unnecessary_change": bool(run.get("deployment")) and actual != expected,
                    "elapsed_seconds": seconds,
                    "agent": run.get("agent_metrics", {}),
                }
            )
        completed = [r for r in items if r["status"] in {"recovered", "blocked", "rejected"}]
        return {
            "note": "Known injected causes are used only for evaluation, never passed to the investigator. Includes human waiting time in elapsed duration. Unnecessary-change metric measures mismatched cause/deployment, not general code minimality.",
            "completed": len(completed),
            "correct_diagnosis": sum(r["correct_diagnosis"] for r in completed),
            "verified_recoveries": sum(r["verified_recovery"] for r in completed),
            "unnecessary_changes": sum(r["unnecessary_change"] for r in completed),
            "runs": items,
        }
