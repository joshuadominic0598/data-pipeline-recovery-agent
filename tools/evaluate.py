"""Run the five known incidents with real Spark and write machine-readable outcomes."""

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

from vitalroute.config import SCENARIOS
from vitalroute.pipeline.executor import spark_session
from vitalroute.recovery.engine import Engine
from vitalroute.recovery.store import Store

def main():
    # Evaluation never sends email, even when the interactive app has Gmail enabled.
    os.environ["EMAIL_MODE"] = "outbox"
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["runbook", "ollama"], default="runbook")
    parser.add_argument("--output", default="artifacts/evaluation.json")
    parser.add_argument("--scenarios", nargs="+", choices=list(SCENARIOS))
    args = parser.parse_args()
    outcomes = []
    spark = spark_session()
    try:
        with tempfile.TemporaryDirectory(prefix="vitalroute-eval-") as directory:
            store = Store(Path(directory))
            engine = Engine(store)
            engine.spark = spark
            for scenario, spec in SCENARIOS.items():
                if scenario == "healthy":
                    continue
                if args.scenarios and scenario not in args.scenarios:
                    continue
                started = time.monotonic()
                run = engine.trigger(scenario, "2026-10-24", args.mode)
                error = None
                try:
                    engine.process(run["id"])
                    run = store.get(run["id"])
                    if run["status"] == "awaiting_approval":
                        # Evaluation harness explicitly plays the owner; production never auto-approves.
                        store.decide(run["id"], run["proposal"]["digest"], True, "evaluation-owner")
                        engine.process(run["id"])
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                run = store.get(run["id"])
                actual = run.get("proposal", {}).get("cause")
                checks = run.get("report", {}).get("checks", [])
                outcome = {
                    "scenario": scenario,
                    "expected": spec["cause"],
                    "diagnosed": actual,
                    "correct_diagnosis": actual == spec["cause"],
                    "verified_recovery": run["status"] == "recovered"
                    and bool(checks)
                    and all(c["passed"] for c in checks),
                    "unnecessary_change": bool(run.get("deployment")) and actual != spec["cause"],
                    "seconds": round(time.monotonic() - started, 2),
                    "metrics": run.get("agent_metrics"),
                    "error": error,
                    "agent_trace": [
                        {"kind": e["kind"], "title": e["title"], "body": e["body"]}
                        for e in store.events(run["id"])
                        if e["kind"] in {"model", "policy_rejection", "diagnosis"}
                    ],
                }
                outcomes.append(outcome)
                print(json.dumps(outcome), flush=True)
    finally:
        spark.stop()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "mode": args.mode,
                "approval": "Evaluation owner explicitly approves policy-gated candidates",
                "outcomes": outcomes,
            },
            indent=2,
        )
    )
    if not all(o["verified_recovery"] and o["correct_diagnosis"] for o in outcomes):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
