# Databricks notebook source
# Workspace integration reference. Requires a configured workspace and UC volume.
import json
import os
import sys
from pathlib import Path

repo_root = Path.cwd().parents[2]
sys.path.insert(0, str(repo_root / "src"))
os.environ.setdefault("VITALROUTE_HOME", str(repo_root))

from vitalroute.config import STAGES, TEMPLATE  # noqa: E402
from vitalroute.pipeline.errors import PipelineFailure  # noqa: E402
from vitalroute.pipeline.executor import execute  # noqa: E402
from vitalroute.pipeline.source import seed  # noqa: E402

for name, default in [
    ("stage", "ingestion"),
    ("source_root", ""),
    ("partition_date", ""),
    ("scenario", "healthy"),
]:
    dbutils.widgets.text(name, default)  # noqa: F821
stage = dbutils.widgets.get("stage")  # noqa: F821
root = Path(dbutils.widgets.get("source_root"))  # noqa: F821
if not str(root).startswith("/Volumes/") or stage not in STAGES:
    raise ValueError("Set a UC volume source_root and a known stage")
if stage == "ingestion":
    seed(root, dbutils.widgets.get("partition_date"), dbutils.widgets.get("scenario"))  # noqa: F821
try:
    result = execute(spark, root, TEMPLATE, root / "production", resume_stage=stage, stop_after=stage)  # noqa: F821
    print(json.dumps(result, default=str))
except PipelineFailure as exc:
    (root / "failure.json").write_text(json.dumps(exc.document(), default=str))
    raise
