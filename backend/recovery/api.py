import os
import secrets
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import ROOT, SCENARIOS, STATE
from .engine import Engine
from .notify import flush, notify
from .store import Store

store = Store(STATE)
engine = Engine(store)
token_file = STATE / "operator-token"
if not token_file.exists():
    token_file.write_text(secrets.token_urlsafe(32))
    token_file.chmod(0o600)
TOKEN = os.getenv("OPERATOR_TOKEN") or token_file.read_text().strip()
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "testserver"}


@asynccontextmanager
async def lifespan(app):
    engine.start()
    yield
    engine.close()


app = FastAPI(title="VitalRoute Recovery", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def local_boundary(request: Request, call_next):
    host = request.headers.get("host", "").split(":")[0]
    if host not in ALLOWED_HOSTS:
        return JSONResponse({"detail": "This demo is restricted to loopback hosts"}, status_code=403)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        from urllib.parse import urlparse

        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Cross-origin actions are blocked"}, status_code=403)
        if not secrets.compare_digest(request.headers.get("x-operator-token", ""), TOKEN):
            return JSONResponse({"detail": "Operator token required"}, status_code=401)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


class Trigger(BaseModel):
    scenario: Literal[
        "healthy", "schema_drift", "duplicates", "missing_partition", "invalid_values", "dependency_down"
    ]
    date: date
    agent_mode: Literal["ollama", "runbook"] = "ollama"
    request_key: str | None = Field(default=None, max_length=100)


class Decision(BaseModel):
    digest: str = Field(min_length=64, max_length=64)
    approve: bool
    actor: str = Field(default="Local pipeline owner", min_length=1, max_length=100)


def get_run(rid):
    try:
        return store.get(rid)
    except KeyError as exc:
        raise HTTPException(404, "Run not found") from exc


@app.get("/api/bootstrap")
def bootstrap(request: Request):
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site bootstrap blocked")
    return {
        "operator_token": TOKEN,
        "scenarios": SCENARIOS,
        "default_mode": os.getenv("AGENT_MODE", "ollama"),
        "today": datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat(),
        "email_mode": os.getenv("EMAIL_MODE", "outbox"),
        "notify_to": os.getenv("NOTIFY_TO", "joshuadominic747@gmail.com"),
        "model": os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        "weather_live": os.getenv("WEATHER_LIVE", "false") == "true",
        "schedule_enabled": os.getenv("DAILY_SCHEDULE_ENABLED", "false") == "true",
        "schedule_hour": os.getenv("DAILY_HOUR_IST", "7"),
        "local_only": True,
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "worker": bool(engine.thread and engine.thread.is_alive()),
        "spark_started": engine.spark is not None,
        "runtime": "Apache Spark 4.0.1 · local[2]",
    }


@app.get("/api/model")
def model():
    try:
        result = httpx.get("http://127.0.0.1:11434/api/tags", timeout=2)
        result.raise_for_status()
        names = [m["name"] for m in result.json()["models"]]
        selected = os.getenv("OLLAMA_MODEL", "qwen3:8b")
        return {"available": selected in names, "model": selected}
    except Exception:
        return {"available": False, "model": os.getenv("OLLAMA_MODEL", "qwen3:8b")}


@app.get("/api/runs")
def runs():
    return store.list()


@app.post("/api/runs", status_code=202)
def trigger(body: Trigger):
    if body.date > datetime.now(ZoneInfo("Asia/Kolkata")).date():
        raise HTTPException(422, "Future source partitions are not available")
    return engine.trigger(body.scenario, body.date.isoformat(), body.agent_mode, body.request_key)


@app.get("/api/runs/{rid}")
def detail(rid: str):
    run = get_run(rid)
    return {**run, "events": store.events(rid), "emails": store.emails(rid)}


@app.get("/api/runs/{rid}/events")
def events(rid: str, after: int = 0):
    get_run(rid)
    return store.events(rid, after)


@app.post("/api/runs/{rid}/decision")
def decision(rid: str, body: Decision):
    get_run(rid)
    try:
        run = store.decide(rid, body.digest, body.approve, body.actor)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    store.event(
        rid,
        "human_decision",
        "Owner approved tested repair" if body.approve else "Owner rejected repair",
        actor=body.actor,
        digest=body.digest,
    )
    if body.approve:
        engine.queue.put(rid)
    else:
        notify(
            store,
            run,
            "repair_rejected",
            "Owner rejected the candidate. No repair was deployed and the previous published data is unchanged.",
        )
        flush(store)
    return run


@app.post("/api/runs/{rid}/retry")
def retry(rid: str):
    run = get_run(rid)
    if run["status"] != "blocked" or run.get("manual_retries", 0) >= 2:
        raise HTTPException(409, "Only blocked runs may be retried, at most twice")
    store.update(rid, status="queued", manual_retries=run.get("manual_retries", 0) + 1, blocker=None)
    store.event(rid, "operator", "Owner requested bounded retry")
    engine.queue.put(rid)
    return {"queued": True}


@app.get("/api/notifications")
def notifications():
    return store.emails()


@app.get("/api/policy")
def policy():
    from .policy import RECIPES

    return {
        "recipes": RECIPES,
        "always_requires_approval": ["Data treatment / quarantine", "Workflow dependency change"],
        "unsupported": [
            "Architectural redesign",
            "New dependencies",
            "Business threshold changes",
            "Arbitrary generated code",
            "Destructive data changes",
        ],
        "enforcement": "Evidence prerequisites + whole-module AST allowlist + sandbox quality gates + digest-bound approval",
    }


@app.get("/api/evaluation")
def evaluation():
    items = []
    for run in store.list():
        expected = SCENARIOS[run["scenario"]].get("cause")
        if not expected:
            continue
        actual = run.get("proposal", {}).get("cause")
        seconds = round(
            (
                datetime.fromisoformat(run.get("finished", run["updated"]))
                - datetime.fromisoformat(run["created"])
            ).total_seconds(),
            2,
        )
        items.append(
            {
                "run_id": run["id"],
                "scenario": run["scenario"],
                "status": run["status"],
                "expected_cause": expected,
                "diagnosed_cause": actual,
                "correct_diagnosis": actual == expected,
                "verified_recovery": run["status"] == "recovered"
                and all(c["passed"] for c in run.get("report", {}).get("checks", [])),
                "unnecessary_change": bool(run.get("deployment")) and actual != expected,
                "elapsed_seconds": seconds,
                "agent": run.get("agent_metrics", {}),
            }
        )
    completed = [r for r in items if r["status"] in {"recovered", "blocked", "rejected"}]
    return {
        "note": "Known injected causes are used only for evaluation, never passed to the investigator. Includes human waiting time in elapsed duration. Unnecessary-change metric measures mismatched cause/deployment, not general code minimality.",
        "completed": len(completed),
        "correct_diagnosis": sum(r["correct_diagnosis"] for r in completed),
        "verified_recoveries": sum(r["verified_recovery"] for r in completed),
        "unnecessary_changes": sum(r["unnecessary_change"] for r in completed),
        "runs": items,
    }


@app.get("/api/runs/{rid}/export")
def export(rid: str):
    run = detail(rid)
    return JSONResponse(run, headers={"Content-Disposition": f'attachment; filename="{rid}-trace.json"'})


dist = ROOT / "frontend/dist"
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")


@app.get("/{path:path}")
def index(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "API endpoint not found")
    if (dist / "index.html").exists():
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})
    return JSONResponse(
        {"message": "Build frontend with npm run build, then restart the server.", "api_docs": "/docs"}
    )
