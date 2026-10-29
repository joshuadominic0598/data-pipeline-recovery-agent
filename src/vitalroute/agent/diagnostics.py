"""Read-only Spark diagnostics for repair evidence."""

import hashlib
import json

from pyspark.sql import functions as F

from ..config import CONTRACT, TEMPLATE
from ..pipeline.source import sha
from .policy import RECIPES

def diagnostic(name, spark, root):
    manifest = json.loads((root / "manifest.json").read_text())
    if name == "read_transform":
        return {
            "file": "pipeline/transform.py",
            "source": TEMPLATE.read_text(),
            "policy": {
                k: {"impact": v["impact"], "requires_approval": v["approval"]} for k, v in RECIPES.items()
            },
        }
    if name == "inspect_manifest":
        path = root / "landing/shipments.json"
        records = spark.read.json(str(path))
        dates = [r[0] for r in records.select("shipment_date").distinct().collect()]
        return {
            "partition": manifest["partition"],
            "inbox_exists": (root / "inbox/shipments.json").exists(),
            "landing_verified": sha(path) == manifest["landing_sha256"],
            "same_partition": dates == [manifest["partition"]],
            "landing_rows": records.count(),
        }
    if name == "probe_dependency":
        registry = json.loads((root / "registry.json").read_text())
        digest = hashlib.sha256(json.dumps(registry["products"], sort_keys=True).encode()).hexdigest()
        return {
            "primary_available": registry["primary_available"],
            "mirror_verified": registry["mirror_available"] and registry["mirror_sha256"] == digest,
            "catalogue_version": registry["version"],
            "note": "Local provider simulator; no external dependency was contacted",
        }
    df = spark.read.json(str(root / "landing/shipments.json"))
    if name == "inspect_schema":
        contract = json.loads(CONTRACT.read_text())
        return {
            "columns": df.columns,
            "schema": df.schema.simpleString(),
            "alias_contract": contract["aliases"] if contract["temperature_unit"] == "Celsius" else {},
            "contract": "contracts/carrier-v2.json; degrees Celsius; same semantic meaning",
        }
    if name == "profile_records":
        temp = "temperature_c" if "temperature_c" in df.columns else "temp_c"
        distinct = df.dropDuplicates()
        conflict = distinct.groupBy("event_id").count().filter("count > 1").count()
        invalid = distinct.filter(
            ~F.col(temp).between(-40, 60)
            | ~F.col("units").between(1, 5000)
            | F.col(temp).isNull()
            | F.col("units").isNull()
        )
        return {
            "rows": df.count(),
            "exact_replays": df.count() - distinct.count(),
            "conflicting_events": conflict,
            "invalid_count": invalid.count(),
            "examples": [r.asDict() for r in invalid.limit(3).collect()],
        }
    raise ValueError("Unknown diagnostic tool")
