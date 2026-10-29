import os
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = PACKAGE_ROOT.parents[1]
DEFAULT_ROOT = SOURCE_ROOT if (SOURCE_ROOT / "pyproject.toml").exists() else Path.cwd()
ROOT = Path(os.getenv("VITALROUTE_HOME", str(DEFAULT_ROOT))).resolve()
load_dotenv(ROOT / ".env")
STATE = Path(os.getenv("STATE_DIR", str(ROOT / ".state"))).resolve()
TEMPLATE = PACKAGE_ROOT / "pipeline/transform.py"
CONTRACT = PACKAGE_ROOT / "pipeline/contracts/carrier-v2.json"
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
