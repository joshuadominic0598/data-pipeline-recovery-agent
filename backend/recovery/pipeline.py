"""A real Spark executor with isolated Parquet checkpoints and publication gates."""

import json
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from .config import STAGES
from .source import input_digest, sha


class PipelineFailure(Exception):
    def __init__(self, stage, code, message, **evidence):
        super().__init__(message)
        self.stage, self.code, self.evidence = stage, code, evidence

    def document(self):
        return {"stage": self.stage, "code": self.code, "message": str(self), "evidence": self.evidence}


def spark_session():
    spark = (
        SparkSession.builder.master("local[2]")
        .appName("VitalRoute")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.driver.memory", "1g")
        .config("spark.sql.session.timeZone", "Asia/Kolkata")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def module(path):
    # Never accepts free-form generated Python; policy checks the entire AST first.
    import types

    result = types.ModuleType("incident_transform")
    exec(compile(Path(path).read_text(), str(path), "exec"), result.__dict__)
    return result


def read_source(spark, root, backfill=False):
    file = root / ("landing/shipments.json" if backfill else "inbox/shipments.json")
    if not file.exists():
        raise PipelineFailure(
            "ingestion",
            "MISSING_PARTITION",
            "Daily partition is missing from the processing inbox",
            partition=json.loads((root / "manifest.json").read_text())["partition"],
        )
    return spark.read.json(str(file))


def execute(spark, root, code, output, emit=lambda *a, **k: None, resume_stage=None, stop_after=None):
    root, output = Path(root), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    transform = module(code)
    manifest = json.loads((root / "manifest.json").read_text())
    registry = json.loads((root / "registry.json").read_text())
    start = STAGES.index(resume_stage) if resume_stage else 0
    if start and not (output / STAGES[start - 1] / "_SUCCESS").exists():
        start = 0
    df = spark.read.parquet(str(output / STAGES[start - 1])) if start else None
    for index, stage in enumerate(STAGES):
        if index < start:
            emit("checkpoint", f"Reuse {stage} checkpoint", stage=stage)
            continue
        emit("stage_start", f"{stage.replace('_', ' ').title()} started", stage=stage)
        try:
            if stage == "ingestion":
                landing = root / "landing/shipments.json"
                if sha(landing) != manifest["landing_sha256"]:
                    raise PipelineFailure(
                        stage, "SOURCE_TAMPERED", "Immutable landing snapshot checksum changed"
                    )
                df = read_source(spark, root, transform.BACKFILL_PARTITION)
                if df.count() != manifest["records"]:
                    raise PipelineFailure(stage, "ROW_COUNT", "Source count differs from manifest")
            elif stage == "cleaning":
                if transform.SOURCE_TEMP_COLUMN not in df.columns:
                    raise PipelineFailure(
                        stage,
                        "UNRESOLVED_COLUMN",
                        f"Cannot resolve {transform.SOURCE_TEMP_COLUMN}",
                        actual_columns=df.columns,
                        expected="temperature_c",
                    )
                df = transform.clean(df)
                count, unique = df.count(), df.select("event_id").distinct().count()
                if count != unique:
                    raise PipelineFailure(
                        stage,
                        "DUPLICATE_EVENTS",
                        "Shipment event IDs are not unique",
                        rows=count,
                        unique_events=unique,
                    )
            elif stage == "preprocessing":
                df, rejected = transform.preprocess(df)
                bad = rejected.count()
                if bad and not transform.QUARANTINE_INVALID:
                    raise PipelineFailure(
                        stage,
                        "INVALID_VALUES",
                        "Impossible sensor readings or invalid shipment units",
                        rejected=bad,
                        examples=[
                            r.asDict()
                            for r in rejected.select("event_id", "temperature_c", "units").limit(3).collect()
                        ],
                    )
                rejected.write.mode("overwrite").parquet(str(output / "quarantine"))
            elif stage == "business_rules":
                available = registry[f"{transform.DEPENDENCY_PROVIDER}_available"]
                if not available:
                    raise PipelineFailure(
                        stage,
                        "DEPENDENCY_UNAVAILABLE",
                        "Product reference registry returned unavailable",
                        provider=transform.DEPENDENCY_PROVIDER,
                        catalogue_version=registry["version"],
                    )
                reference = spark.createDataFrame(registry["products"])
                df = transform.apply_rules(df, reference)
            else:
                df = transform.prepare_product(df)
            df.write.mode("overwrite").parquet(str(output / stage))
            # Materialize before advancing the checkpoint; avoid retaining an overwrite lineage.
            df = spark.read.parquet(str(output / stage))
            emit(
                "stage_done",
                f"{stage.replace('_', ' ').title()} completed",
                stage=stage,
                rows=df.count(),
                artifact=f"{stage}/part-*.parquet",
            )
            if stage == stop_after and stage != "consumption":
                return {"checkpoint": stage, "rows": df.count()}
        except PipelineFailure:
            raise
        except Exception as exc:
            raise PipelineFailure(stage, "SPARK_EXECUTION_ERROR", str(exc)[:1800]) from exc
    checks, metrics = validate(spark, root, output)
    emit("quality", "Validate downstream data product", checks=checks, metrics=metrics)
    if not all(c["passed"] for c in checks):
        raise PipelineFailure(
            "consumption", "QUALITY_GATE", "Job completed but recovery quality gates failed", checks=checks
        )
    rows = json.loads(
        json.dumps(
            [r.asDict() for r in df.orderBy(F.desc("risk_score"), "event_id").limit(12).collect()],
            default=str,
        )
    )
    report = {
        "checks": checks,
        "metrics": metrics,
        "sample": rows,
        "output": str(output / "consumption"),
        "executed_code_sha256": sha(code),
        "input_digest": input_digest(root),
    }
    (output / "validation.json").write_text(json.dumps(report, default=str, indent=2))
    return report


def validate(spark, root, output):
    manifest = json.loads((root / "manifest.json").read_text())
    df = spark.read.parquet(str(output / "consumption"))
    rejected = spark.read.parquet(str(output / "quarantine"))
    row_count = df.count()
    unique = df.select("event_id").distinct().count()
    quarantined = rejected.select("event_id").distinct().count()
    from functools import reduce

    nulls = df.filter(reduce(lambda a, b: a | b, [F.col(c).isNull() for c in df.columns])).count()
    invalid = df.filter(~F.col("temperature_c").between(-40, 60) | ~F.col("units").between(1, 5000)).count()
    stale = df.filter(
        F.col("shipment_date").isNull()
        | (F.col("shipment_date") != F.lit(manifest["partition"]).cast("date"))
    ).count()
    breach = ~F.col("temperature_c").between(2, 8)
    expected_usable = F.when(~breach & (F.col("days_to_expiry") > 0), F.col("units")).otherwise(0)
    expected_action = (
        F.when(breach, "hold_for_review").when(F.col("days_to_expiry") < 7, "expedite").otherwise("release")
    )
    expected_risk = F.when(breach, 90).when(F.col("days_to_expiry") < 7, 65).otherwise(15)
    invalid_rules = df.filter(
        (F.col("cold_chain_breach") != breach)
        | (F.col("usable_units") != expected_usable)
        | (F.col("action") != expected_action)
        | (F.col("risk_score") != expected_risk)
    ).count()
    overlap = df.join(rejected.select("event_id"), "event_id", "inner").count()
    agg = df.agg(
        F.sum("units").alias("units"),
        F.sum("usable_units").alias("usable"),
        F.sum(F.col("cold_chain_breach").cast("int")).alias("holds"),
    ).first()
    source = read_source(spark, root, backfill=True)
    missing = (
        source.select("event_id")
        .distinct()
        .join(df.select("event_id").union(rejected.select("event_id")).distinct(), "event_id", "left_anti")
        .count()
    )
    checks = [
        {
            "name": "Row-count reconciliation",
            "passed": row_count + quarantined == manifest["unique_events"],
            "detail": f"{row_count} accepted + {quarantined} quarantined = {manifest['unique_events']} expected events",
        },
        {
            "name": "Unique event IDs",
            "passed": unique == row_count,
            "detail": f"{row_count - unique} duplicates",
        },
        {
            "name": "Partition freshness",
            "passed": stale == 0,
            "detail": f"All rows belong to {manifest['partition']}",
        },
        {
            "name": "Required fields & product coverage",
            "passed": nulls == 0,
            "detail": f"{nulls} missing required values",
        },
        {
            "name": "Plausible source values",
            "passed": invalid == 0,
            "detail": f"{invalid} impossible readings",
        },
        {
            "name": "Cold-chain business rules",
            "passed": invalid_rules == 0,
            "detail": f"{invalid_rules} violations; held shipments have zero usable units",
        },
        {
            "name": "Event conservation",
            "passed": missing == 0 and overlap == 0,
            "detail": f"{missing} lost events; {overlap} quarantine overlaps",
        },
    ]
    metrics = {
        "rows": row_count,
        "quarantined": quarantined,
        "units": agg["units"],
        "usable_units": agg["usable"],
        "holds": agg["holds"],
        "facilities": df.select("facility").distinct().count(),
        "partition": manifest["partition"],
    }
    return checks, metrics
