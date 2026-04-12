"""
AeroCorridor — root entry point.

Dual role:
  1. FastAPI application object (`app`) — loaded by uvicorn as `main:app`
  2. Process launcher (`python main.py`) — spawns uvicorn + Streamlit
"""

import os
import subprocess
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.database import init_db
from backend.app.routers.buildings import router as buildings_router
from backend.app.routers.delivery_nodes import router as nodes_router
from backend.app.routers.map import router as map_router
from backend.app.routers.orders import router as orders_router
from backend.app.routers.routes import router as routes_router
from backend.app.routers.setup import router as setup_router
from backend.app.routers.swarm_hybrid import router as swarm_hybrid_router
from backend.app.routers.swarm_obstacles import router as swarm_obstacles_router
from backend.app.routers.telemetry import router as telemetry_router

# ─────────────────────────────────────────────────────────────────────────────
#  Lifespan (startup / shutdown)
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    try:
        init_db()
    except Exception as exc:
        print(f"[startup] DB init warning: {exc}")

    if settings.AUTO_BOOTSTRAP:
        try:
            from backend.app.database import SessionLocal
            from backend.app.services.demo_bootstrap import ensure_demo_data
            db = SessionLocal()
            try:
                result = ensure_demo_data(db)
                print(f"[startup] Bootstrap: {result}")
            finally:
                db.close()
        except Exception as exc:
            print(f"[startup] Bootstrap warning: {exc}")

    yield
    # ── Shutdown (nothing to clean up for now) ────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
#  FastAPI application
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AeroCorridor drone delivery platform — REST + WebSocket API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Existing routers ──────────────────────────────────────────────────────────
_PREFIX = settings.API_V1_PREFIX   # "/api/v1"

app.include_router(buildings_router, prefix=_PREFIX)
app.include_router(nodes_router,     prefix=_PREFIX)
app.include_router(orders_router,    prefix=_PREFIX)
app.include_router(routes_router,    prefix=_PREFIX)
app.include_router(map_router,       prefix=_PREFIX)
app.include_router(telemetry_router, prefix=_PREFIX)
app.include_router(setup_router,     prefix=_PREFIX)

# ── Swarm simulation routers ──────────────────────────────────────────────────
app.include_router(swarm_hybrid_router,    prefix=_PREFIX)
app.include_router(swarm_obstacles_router, prefix=_PREFIX)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": settings.VERSION, "project": settings.PROJECT_NAME}


# ─────────────────────────────────────────────────────────────────────────────
#  Process launcher  (python main.py)
# ─────────────────────────────────────────────────────────────────────────────

def launch():
    """Spawn uvicorn (backend) and Streamlit (frontend) as child processes."""
    cwd = os.getcwd()
    print("Starting AeroCorridor Backend and Frontend...")

    backend_proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "main:app",                  # ← points to this file's `app`
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
        ],
        cwd=cwd,
    )

    time.sleep(2)   # give uvicorn a moment before starting Streamlit

    frontend_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "frontend/home.py"],
        cwd=cwd,
    )

    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait()
        frontend_proc.wait()
        print("Servers stopped.")


if __name__ == "__main__":
    launch()
