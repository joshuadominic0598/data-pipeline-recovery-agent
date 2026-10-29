from datetime import date

from fastapi.testclient import TestClient

from vitalroute.api.app import create_app
from vitalroute.recovery.engine import Engine
from vitalroute.recovery.store import Store

def test_operator_boundary_and_stale_approval(tmp_path):
    isolated = Store(tmp_path)
    # No lifespan is run: this tests HTTP boundaries without starting another Spark worker.
    client = TestClient(create_app(isolated, Engine(isolated)))
    body = {"scenario": "schema_drift", "date": date.today().isoformat(), "agent_mode": "runbook"}
    assert client.post("/api/runs", json=body).status_code == 401
    token = client.get("/api/bootstrap").json()["operator_token"]
    headers = {"x-operator-token": token}
    assert (
        client.post("/api/runs", json=body, headers={**headers, "origin": "https://evil.example"}).status_code
        == 403
    )
    assert client.get("/api/bootstrap", headers={"sec-fetch-site": "cross-site"}).status_code == 403
    assert client.get("/api/health", headers={"host": "evil.example"}).status_code == 403
    run = client.post("/api/runs", json=body, headers=headers).json()
    assert (
        client.post(
            f"/api/runs/{run['id']}/decision", headers=headers, json={"digest": "0" * 64, "approve": True}
        ).status_code
        == 409
    )
    assert client.get("/api/runs/unknown").status_code == 404
    assert client.get("/api/nonexistent").status_code == 404

def test_application_instances_keep_state_and_tokens_separate(tmp_path, monkeypatch):
    monkeypatch.delenv("OPERATOR_TOKEN", raising=False)
    first = TestClient(create_app(Store(tmp_path / "first")))
    second = TestClient(create_app(Store(tmp_path / "second")))
    first_token = first.get("/api/bootstrap").json()["operator_token"]
    second_token = second.get("/api/bootstrap").json()["operator_token"]
    assert first_token != second_token
    body = {"scenario": "healthy", "date": date.today().isoformat(), "agent_mode": "runbook"}
    headers = {"x-operator-token": first_token}
    response = first.post("/api/runs", json=body, headers=headers)
    assert response.status_code == 202
    assert len(first.get("/api/runs").json()) == 1
    assert second.get("/api/runs").json() == []
    assert second.post("/api/runs", json=body, headers=headers).status_code == 401
    run_id = response.json()["id"]
    assert first.get(f"/api/runs/{run_id}/export").json()["id"] == run_id
    assert second.get(f"/api/runs/{run_id}").status_code == 404

def test_importing_application_creates_no_runtime_state(tmp_path):
    import os
    import subprocess
    import sys

    state = tmp_path / "unused-state"
    environment = {**os.environ, "STATE_DIR": str(state)}
    subprocess.run([sys.executable, "-c", "import vitalroute.api.app"], env=environment, check=True)
    assert not state.exists()
