# Databricks notebook source
# ruff: noqa: F821
"""Hosted investigator: saves a tested candidate for a separate promotion service.

The reference defaults to the no-model runbook investigator. This notebook never
edits a running job, pushes a branch, or auto-approves dependency/data changes.
"""

import json
import sys
from pathlib import Path

repo_root = Path.cwd().parents[1]
sys.path.insert(0, str(repo_root / "backend"))

from recovery.agent import investigate  # noqa: E402
from recovery.pipeline import execute  # noqa: E402
from recovery.policy import RECIPES, patch, proposal_digest  # noqa: E402
from recovery.source import input_digest, sha  # noqa: E402
from recovery.store import now  # noqa: E402

dbutils.widgets.text("source_root", "")  # noqa: F821
dbutils.widgets.text("job_run_id", "")  # noqa: F821
root = Path(dbutils.widgets.get("source_root"))  # noqa: F821
if not str(root).startswith("/Volumes/"):
    raise ValueError("source_root must be a UC volume directory")
failure = json.loads((root / "failure.json").read_text())
events = []


def emit(kind, title, **body):
    events.append({"time": now(), "kind": kind, "title": title, "body": json.dumps(body, default=str)})
    print(json.dumps(events[-1]))


try:
    recipe, rationale, metrics, observations = investigate(spark, root, failure, emit, "runbook")  # noqa: F821
    code, diff = patch(recipe)
    candidate = root / "candidate.py"
    candidate.write_text(code)
    report = execute(spark, root, candidate, root / "sandbox", emit)  # noqa: F821
    spec = RECIPES[recipe]
    proposal = {
        "job_run_id": dbutils.widgets.get("job_run_id"),
        "recipe": recipe,
        "requires_approval": spec["approval"],
        "rationale": rationale,
        "impact": spec["impact"],
        "diff": diff,
        "digest": proposal_digest(code, input_digest(root)),
        "code_sha256": sha(candidate),
        "input_digest": input_digest(root),
        "sandbox": report,
        "metrics": metrics,
        "status": "awaiting_owner_approval" if spec["approval"] else "ready_for_promotion_service",
    }  # noqa: F821
    (root / "proposal.json").write_text(json.dumps(proposal, default=str, indent=2))
    print(
        json.dumps(
            {
                "status": proposal["status"],
                "digest": proposal["digest"],
                "note": "A separately authorized promotion service must commit, deploy and repair this run.",
            }
        )
    )
finally:
    if events:
        spark.createDataFrame(events).write.format("delta").mode("append").save(
            str(root.parent / "recovery_events")
        )  # noqa: F821
