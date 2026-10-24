from datetime import date

from fastapi.testclient import TestClient
from recovery import api
from recovery.engine import Engine
from recovery.store import Store


def test_operator_boundary_and_stale_approval(tmp_path, monkeypatch):
    isolated = Store(tmp_path)
    monkeypatch.setattr(api, "store", isolated)
    monkeypatch.setattr(api, "engine", Engine(isolated))
    # No lifespan is run: this tests HTTP boundaries without starting another Spark worker.
    client = TestClient(api.app)
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
