import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
STATE = Path(os.getenv("STATE_DIR", str(ROOT / ".state"))).resolve()
TEMPLATE = ROOT / "backend/pipeline/transform.py"
STAGES = ["ingestion", "cleaning", "preprocessing", "business_rules", "consumption"]
SCENARIOS = {
    "healthy": {"label": "Healthy refresh", "description": "Run the daily feed through every quality gate."},
    "schema_drift": {
        "label": "Renamed source column",
        "description": "Carrier publishes temp_c instead of temperature_c.",
        "cause": "schema_drift",
    },
    "duplicates": {
        "label": "Replayed shipment events",
        "description": "A connector replays exact duplicate delivery events.",
        "cause": "duplicates",
    },
    "missing_partition": {
        "label": "Missing daily partition",
        "description": "A landed partition is absent from the processing inbox.",
        "cause": "missing_partition",
    },
    "invalid_values": {
        "label": "Invalid sensor readings",
        "description": "Impossible temperatures and negative shipment quantities.",
        "cause": "invalid_values",
    },
    "dependency_down": {
        "label": "Product registry unavailable",
        "description": "The primary product reference service is offline.",
        "cause": "dependency_down",
    },
}
