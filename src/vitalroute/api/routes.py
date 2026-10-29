"""Thin HTTP endpoints for the recovery application."""

import os
from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from ..config import SCENARIOS
from ..recovery.service import RecoveryService
from .schemas import Decision, Trigger

router = APIRouter(prefix="/api")

def get_service(request: Request):
    return request.app.state.recovery

Service = Annotated[RecoveryService, Depends(get_service)]

@router.get("/bootstrap")
def bootstrap(request: Request):
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site bootstrap blocked")
    return {
        "operator_token": request.app.state.operator_token,
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

@router.get("/health")
def health(service: Service):
    engine = service.engine
    return {
        "status": "ok",
        "worker": bool(engine.thread and engine.thread.is_alive()),
        "spark_started": engine.spark is not None,
        "runtime": "Apache Spark 4.0.1 · local[2]",
    }

@router.get("/model")
def model():
    try:
        result = httpx.get("http://127.0.0.1:11434/api/tags", timeout=2)
        result.raise_for_status()
        names = [m["name"] for m in result.json()["models"]]
        selected = os.getenv("OLLAMA_MODEL", "qwen3:8b")
        return {"available": selected in names, "model": selected}
    except Exception:
        return {"available": False, "model": os.getenv("OLLAMA_MODEL", "qwen3:8b")}

@router.get("/runs")
def runs(service: Service):
    return service.store.list()

@router.post("/runs", status_code=202)
def trigger(body: Trigger, service: Service):
    if body.date > datetime.now(ZoneInfo("Asia/Kolkata")).date():
        raise HTTPException(422, "Future source partitions are not available")
    return service.engine.trigger(body.scenario, body.date.isoformat(), body.agent_mode, body.request_key)

@router.get("/runs/{rid}")
def detail(rid: str, service: Service):
    return service.detail(rid)

@router.get("/runs/{rid}/events")
def events(rid: str, service: Service, after: int = 0):
    return service.events(rid, after)

@router.post("/runs/{rid}/decision")
def decision(rid: str, body: Decision, service: Service):
    return service.decide(rid, body.digest, body.approve, body.actor)

@router.post("/runs/{rid}/retry")
def retry(rid: str, service: Service):
    return service.retry(rid)

@router.get("/notifications")
def notifications(service: Service):
    return service.store.emails()

@router.get("/policy")
def policy():
    from ..agent.policy import RECIPES

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

@router.get("/evaluation")
def evaluation(service: Service):
    return service.evaluation()

@router.get("/runs/{rid}/export")
def export(rid: str, service: Service):
    return JSONResponse(
        service.detail(rid), headers={"Content-Disposition": f'attachment; filename="{rid}-trace.json"'}
    )
