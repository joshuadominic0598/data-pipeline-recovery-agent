import json
import subprocess

import pytest

from vitalroute.agent.policy import eligible, patch, verify_patch
from vitalroute.config import TEMPLATE
from vitalroute.pipeline.source import input_digest
from vitalroute.recovery.engine import Engine
from vitalroute.recovery.store import Store

def incident(tmp_path, spark, scenario):
    store = Store(tmp_path)
    engine = Engine(store)
    engine.spark = spark
    run = engine.trigger(scenario, "2026-10-24", "runbook")
    engine.process(run["id"])
    return store, engine, run["id"]

@pytest.mark.parametrize(
    "scenario,expected,approval,rows",
    [
        ("schema_drift", "schema_drift", False, 192),
        ("duplicates", "duplicates", False, 192),
        ("missing_partition", "missing_partition", False, 192),
        ("invalid_values", "invalid_values", True, 190),
        ("dependency_down", "dependency_down", True, 192),
    ],
)
def test_real_spark_recovery_and_persisted_approval(tmp_path, spark, scenario, expected, approval, rows):
    store, engine, rid = incident(tmp_path, spark, scenario)
    run = store.get(rid)
    assert run["proposal"]["cause"] == expected
    assert run["proposal"]["requires_approval"] == approval
    assert all(c["passed"] for c in run["sandbox"]["checks"])
    if approval:
        assert run["status"] == "awaiting_approval"
        assert not run.get("deployment")
        assert not (tmp_path / "published.json").exists()
        # Reconstruct both state and orchestrator, as after a restart; no in-memory approval state.
        store = Store(tmp_path)
        engine = Engine(store)
        engine.spark = spark
        store.decide(rid, run["proposal"]["digest"], True, "test-owner")
        engine.process(rid)
        run = store.get(rid)
    assert run["status"] == "recovered"
    assert run["report"]["metrics"]["rows"] == rows
    assert all(c["passed"] for c in run["report"]["checks"])
    assert set(run["stages"].values()) == {"passed"}
    assert json.loads((tmp_path / "published.json").read_text())["run_id"] == rid
    assert run["deployment"]["github_push"] is False
    assert run["deployment"]["databricks_deploy"] is False
    assert (
        subprocess.check_output(
            ["git", "-C", str(tmp_path / "runs" / rid / "release"), "rev-parse", "HEAD"], text=True
        ).strip()
        == run["deployment"]["commit"]
    )
    assert (
        any(e["kind"] == "checkpoint" for e in store.events(rid)) if scenario != "missing_partition" else True
    )
    assert {m["kind"] for m in store.emails(rid)} >= {"pipeline_failed", "recovery_verified"}

def test_healthy_run_needs_no_agent_or_change(tmp_path, spark):
    store, _, rid = incident(tmp_path, spark, "healthy")
    run = store.get(rid)
    assert run["status"] == "succeeded"
    assert not run.get("proposal") and not run.get("deployment")
    assert run["report"]["metrics"]["rows"] == 192

def test_rejected_approval_never_deploys(tmp_path, spark):
    store, engine, rid = incident(tmp_path, spark, "dependency_down")
    run = store.get(rid)
    store.decide(rid, run["proposal"]["digest"], False, "owner")
    assert store.get(rid)["status"] == "rejected"
    assert not store.get(rid).get("deployment")
    with pytest.raises(ValueError, match="stale"):
        store.decide(rid, run["proposal"]["digest"], True, "owner")
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from promotion_plan import plan

    with pytest.raises(ValueError, match="approval"):
        plan(tmp_path, rid, 123)

def test_changed_input_cannot_reuse_approval(tmp_path, spark):
    store, engine, rid = incident(tmp_path, spark, "invalid_values")
    run = store.get(rid)
    store.decide(rid, run["proposal"]["digest"], True, "owner")
    path = tmp_path / "runs" / rid
    before = input_digest(path)
    with (path / "landing/shipments.json").open("a") as file:
        file.write("{}\n")
    assert input_digest(path) != before
    with pytest.raises(ValueError, match="changed"):
        engine.process(rid)
    assert not store.get(rid).get("deployment")

def test_no_quality_regression_in_unaffected_events(tmp_path, spark):
    store, _, rid = incident(tmp_path, spark, "duplicates")
    from vitalroute.pipeline.executor import execute
    from vitalroute.pipeline.source import seed

    baseline = tmp_path / "healthy"
    seed(baseline, "2026-10-24", "healthy")
    report = execute(spark, baseline, TEMPLATE, baseline / "output")
    repaired = spark.read.parquet(store.get(rid)["report"]["output"])
    healthy = spark.read.parquet(report["output"])
    assert repaired.exceptAll(healthy).count() == 0
    assert healthy.exceptAll(repaired).count() == 0

@pytest.mark.parametrize(
    "recipe", ["column_alias", "exact_dedup", "replay_partition", "quarantine_invalid", "registry_mirror"]
)
def test_patch_scope_is_enforced(recipe):
    code, diff = patch(recipe)
    assert "+" in diff
    verify_patch(code, recipe)
    with pytest.raises(ValueError):
        verify_patch(code + "\nimport subprocess\n", recipe)
    with pytest.raises(ValueError):
        verify_patch(code.replace("between(2, 8)", "between(2, 15)"), recipe)

def test_conflicting_replays_and_unknown_edits_fail_closed():
    assert not eligible("exact_dedup", {"profile_records": {"exact_replays": 12, "conflicting_events": 1}})
    assert not eligible(
        "registry_mirror", {"probe_dependency": {"primary_available": False, "mirror_verified": False}}
    )
    assert not eligible(
        "column_alias",
        {"inspect_schema": {"columns": ["temperature_f"], "alias_contract": {"temp_c": "temperature_c"}}},
    )
    assert not eligible("invented_repair", {})

def test_trigger_and_email_idempotency(tmp_path):
    store = Store(tmp_path)
    engine = Engine(store)
    one = engine.trigger("healthy", "2026-10-24", "runbook", "source-event-1")
    two = engine.trigger("healthy", "2026-10-24", "runbook", "source-event-1")
    assert one["id"] == two["id"]
    assert len(store.list()) == 1
    store.queue_email(one["id"], "failure", {"body": "one"})
    store.queue_email(one["id"], "failure", {"body": "two"})
    assert len(store.emails()) == 1
    assert store.claim_email(one["id"] + "-failure")
    assert not store.claim_email(one["id"] + "-failure")

def test_successful_spark_write_is_not_verified_recovery(tmp_path, spark):
    from pyspark.sql import functions as F

    from vitalroute.pipeline.executor import execute
    from vitalroute.pipeline.quality import validate
    from vitalroute.pipeline.source import seed

    seed(tmp_path, "2026-10-24", "healthy")
    output = tmp_path / "output"
    execute(spark, tmp_path, TEMPLATE, output)
    gold = spark.read.parquet(str(output / "consumption"))
    # A syntactically successful job writes duplicated data and corrupts usable inventory.
    corrupted = gold.withColumn("usable_units", F.lit(99999)).unionByName(gold.limit(1))
    corrupted.write.mode("overwrite").parquet(str(output / "bad-product"))
    import shutil

    shutil.rmtree(output / "consumption")
    (output / "bad-product").rename(output / "consumption")
    checks, _ = validate(spark, tmp_path, output)
    failed = {c["name"] for c in checks if not c["passed"]}
    assert {"Row-count reconciliation", "Unique event IDs", "Cold-chain business rules"} <= failed
