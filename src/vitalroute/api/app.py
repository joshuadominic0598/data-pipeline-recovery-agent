"""Application composition and local HTTP security boundary."""

import os
import secrets
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ..config import ROOT, STATE
from ..recovery.engine import Engine
from ..recovery.service import RecoveryConflict, RecoveryService, RunNotFound
from ..recovery.store import Store
from .routes import router

ALLOWED_HOSTS = {"127.0.0.1", "localhost", "testserver"}

def create_app(store=None, engine=None):
    store = store if store is not None else Store(STATE)
    engine = engine if engine is not None else Engine(store)
    token_file = store.root / "operator-token"
    if not token_file.exists():
        token_file.write_text(secrets.token_urlsafe(32))
        token_file.chmod(0o600)
    token = os.getenv("OPERATOR_TOKEN") or token_file.read_text().strip()

    @asynccontextmanager
    async def lifespan(app):
        engine.start()
        yield
        engine.close()

    app = FastAPI(title="VitalRoute Recovery", version="0.1.0", lifespan=lifespan)
    app.state.recovery = RecoveryService(store, engine)
    app.state.operator_token = token
    app.middleware("http")(local_boundary)
    app.add_exception_handler(RunNotFound, not_found)
    app.add_exception_handler(RecoveryConflict, conflict)
    app.include_router(router)
    static_dir = ROOT / "frontend/dist"
    if static_dir.exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{path:path}")
    def index(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "API endpoint not found")
        if (static_dir / "index.html").exists():
            return FileResponse(static_dir / "index.html", headers={"Cache-Control": "no-cache"})
        return JSONResponse(
            {"message": "Build frontend with npm run build, then restart the server.", "api_docs": "/docs"}
        )

    return app

async def local_boundary(request: Request, call_next):
    host = request.headers.get("host", "").split(":")[0]
    if host not in ALLOWED_HOSTS:
        return JSONResponse({"detail": "This demo is restricted to loopback hosts"}, status_code=403)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Cross-origin actions are blocked"}, status_code=403)
        if not secrets.compare_digest(
            request.headers.get("x-operator-token", ""), request.app.state.operator_token
        ):
            return JSONResponse({"detail": "Operator token required"}, status_code=401)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response

async def not_found(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=404)

async def conflict(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=409)
