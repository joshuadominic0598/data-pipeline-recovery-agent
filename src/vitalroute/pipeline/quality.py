"""Independent checks for the final consumption data product."""

import json
from functools import reduce

from pyspark.sql import functions as F

from .source import read_source

def validate(spark, root, output):
    manifest = json.loads((root / "manifest.json").read_text())
    df = spark.read.parquet(str(output / "consumption"))
    rejected = spark.read.parquet(str(output / "quarantine"))
    row_count = df.count()
    unique = df.select("event_id").distinct().count()
    quarantined = rejected.select("event_id").distinct().count()
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
