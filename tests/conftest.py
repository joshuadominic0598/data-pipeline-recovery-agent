import os
from pathlib import Path

import pytest

@pytest.fixture(autouse=True)
def no_email_delivery(monkeypatch):
    monkeypatch.setenv("EMAIL_MODE", "outbox")

@pytest.fixture(scope="session")
def spark():
    root = Path(__file__).resolve().parents[1]
    if not os.getenv("JAVA_HOME"):
        candidates = list((root / ".tools").glob("jdk-*/Contents/Home")) + list(
            (root / ".tools").glob("jdk-*/")
        )
        if candidates:
            os.environ["JAVA_HOME"] = str(candidates[0])
    os.environ.setdefault("PYSPARK_PYTHON", str(root / ".venv/bin/python"))
    from vitalroute.pipeline.executor import spark_session

    session = spark_session()
    yield session
    session.stop()
