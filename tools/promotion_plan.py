"""Render a Databricks promotion plan from a tested local incident. Never executes it."""

import argparse
import json
from pathlib import Path

from vitalroute.agent.policy import RECIPES, proposal_digest, verify_patch
from vitalroute.pipeline.source import input_digest
from vitalroute.recovery.store import Store

def plan(state, rid, cloud_run_id):
    store = Store(Path(state))
    run = store.get(rid)
    proposal = run.get("proposal")
    if not proposal or not run.get("sandbox") or not all(c["passed"] for c in run["sandbox"]["checks"]):
        raise ValueError("A tested proposal with passing quality gates is required")
    root = Path(state) / "runs" / rid
    code = (root / "candidate.py").read_text()
    verify_patch(code, proposal["recipe"])
    if proposal_digest(code, input_digest(root)) != proposal["digest"]:
        raise ValueError("Tested code or inputs have changed")
    if RECIPES[proposal["recipe"]]["approval"] and (
        not run.get("approval", {}).get("approved")
        or run.get("approval", {}).get("digest") != proposal["digest"]
    ):
        raise ValueError("Owner approval of the exact proposal is required")
    return {
        "mode": "plan_only",
        "tested_digest": proposal["digest"],
        "repository": "joshuadominic0598/data-pipeline-recovery-agent",
        "branch": f"codex/recovery-{rid.lower()}",
        "code_change": "Apply the tested diff to src/vitalroute/pipeline/transform.py in a clean checkout at a leased base SHA",
        "promotion_steps": [
            "Create a GitHub commit/PR with evidence, checks and approval digest; honor branch protections",
            "CI runs unit/integration tests and Databricks sandbox job on that exact commit",
            "Authorized deployment identity checks the approval again and deploys the same checkout",
        ],
        "bundle_directory": "tools/databricks",
        "cli_argv": [
            ["databricks", "bundle", "validate", "--target", "dev"],
            ["databricks", "bundle", "deploy", "--target", "dev"],
            [
                "databricks",
                "jobs",
                "repair-run",
                "--json",
                json.dumps(
                    {
                        "run_id": cloud_run_id,
                        "rerun_tasks": [run["failure"]["stage"]],
                        "rerun_dependent_tasks": True,
                    }
                ),
            ],
        ],
        "verification": "Poll the repaired attempt; require SUCCESS, fresh validation.json with the approved code hash and source digest, and all seven data checks. Repeated repairs must include latest_repair_id from the current job run.",
        "required_services": [
            "Workspace authentication",
            "Existing cluster/compute",
            "UC volume and Delta approval store",
            "GitHub deployment identity and protected environment",
            "Identity-backed approval UI",
            "Notification credentials",
        ],
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default=".state")
    parser.add_argument("--incident", required=True)
    parser.add_argument("--databricks-run-id", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(plan(args.state, args.incident, args.databricks_run_id), indent=2))
