"""Versioned PySpark transformation. Recovery can edit only reviewed settings below."""

from pyspark.sql import functions as F

SOURCE_TEMP_COLUMN = "temperature_c"
DEDUPLICATE_EXACT = False
QUARANTINE_INVALID = False
BACKFILL_PARTITION = False
DEPENDENCY_PROVIDER = "primary"


def clean(df):
    df = df.withColumnRenamed(SOURCE_TEMP_COLUMN, "temperature_c")
    df = df.withColumn("facility", F.trim(F.col("facility")))
    if DEDUPLICATE_EXACT:
        df = df.dropDuplicates()
    return df


def preprocess(df):
    valid = F.col("units").between(1, 5000) & F.col("temperature_c").between(-40, 60)
    rejected = df.filter(~valid | F.col("temperature_c").isNull() | F.col("units").isNull())
    if QUARANTINE_INVALID:
        df = df.filter(valid)
    return df.withColumn("shipment_date", F.to_date("shipment_date")), rejected


def apply_rules(df, reference):
    return (
        df.join(reference, "product_id", "left")
        .withColumn("cold_chain_breach", ~F.col("temperature_c").between(2, 8))
        .withColumn("days_to_expiry", F.datediff("expiry_date", "shipment_date"))
        .withColumn(
            "usable_units",
            F.when(~F.col("cold_chain_breach") & (F.col("days_to_expiry") > 0), F.col("units")).otherwise(0),
        )
        .withColumn(
            "risk_score",
            F.when(F.col("cold_chain_breach"), 90).when(F.col("days_to_expiry") < 7, 65).otherwise(15),
        )
        .withColumn(
            "action",
            F.when(F.col("cold_chain_breach"), "hold_for_review")
            .when(F.col("days_to_expiry") < 7, "expedite")
            .otherwise("release"),
        )
    )


def prepare_product(df):
    return df.select(
        "event_id",
        "shipment_date",
        "facility",
        "city",
        "product_id",
        "product_name",
        "units",
        "temperature_c",
        "ambient_c",
        "days_to_expiry",
        "cold_chain_breach",
        "usable_units",
        "risk_score",
        "action",
    )
