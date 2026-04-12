"""
Hybrid Swarm simulation router.

Endpoints
---------
POST   /api/v1/swarm/hybrid/start
    Create a new simulation session (pre-computes all frames).
    Returns session_id + total frame count.

GET    /api/v1/swarm/hybrid/{session_id}/frame/{k}
    Fetch a specific pre-computed frame as JSON.

WS     /api/v1/swarm/hybrid/{session_id}/stream
    Stream all frames over a WebSocket at the simulation's native dt.

DELETE /api/v1/swarm/hybrid/{session_id}
    Destroy a session and free memory.

GET    /api/v1/swarm/hybrid/sessions
    List active session count (diagnostics).
"""

import asyncio
import dataclasses
import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..services.hybrid_swarm_sim import HybridSwarmSim
from ..services import sim_session_store as store

router = APIRouter(prefix="/swarm/hybrid", tags=["swarm_hybrid"])


# ── Request / response schemas ────────────────────────────────────────────────

class StartRequest(BaseModel):
    n_drones:     int   = Field(default=3, ge=1, le=10)
    total_time_s: float = Field(default=120.0, gt=0)
    dt:           float = Field(default=0.2, gt=0)
    seed:         int   = Field(default=42)


class StartResponse(BaseModel):
    session_id:  str
    n_drones:    int
    total_steps: int
    total_time_s: float
    dt:          float


# ── Helper: dataclass → JSON-serialisable dict ────────────────────────────────

def _frame_to_dict(frame) -> dict:
    return dataclasses.asdict(frame)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/start", response_model=StartResponse)
async def start_simulation(body: StartRequest):
    """
    Pre-compute a full hybrid swarm simulation and store it in memory.
    Returns a session_id for subsequent frame fetches or WebSocket streaming.
    """
    sim    = HybridSwarmSim(
        n_drones=body.n_drones,
        total_time_s=body.total_time_s,
        dt=body.dt,
        seed=body.seed,
    )
    result = sim.run()
    sid    = store.store_hybrid(result)

    return StartResponse(
        session_id=sid,
        n_drones=result.n_drones,
        total_steps=result.steps,
        total_time_s=result.total_time_s,
        dt=result.dt,
    )


@router.get("/{session_id}/frame/{k}")
async def get_frame(session_id: str, k: int):
    """Return a single pre-computed frame as JSON."""
    result = store.get_hybrid(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")

    frame = result.get_frame(k)
    if frame is None:
        raise HTTPException(status_code=404, detail=f"Frame {k} out of range (0–{result.steps - 1})")

    return _frame_to_dict(frame)


@router.websocket("/{session_id}/stream")
async def stream_simulation(websocket: WebSocket, session_id: str):
    """
    Stream all pre-computed frames over WebSocket.
    Sends one JSON message per frame, paced at the simulation's dt interval.
    Closes cleanly when all frames are sent or the client disconnects.
    """
    result = store.get_hybrid(session_id)
    if result is None:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()

    try:
        for frame in result.frames:
            await websocket.send_text(json.dumps(_frame_to_dict(frame)))
            await asyncio.sleep(result.dt)

        # Signal completion
        await websocket.send_json({"type": "done", "total_frames": result.steps})
        await websocket.close()

    except WebSocketDisconnect:
        pass   # client closed — nothing to clean up (result stays in store)


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Remove a session from memory."""
    removed = store.delete_hybrid(session_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": session_id}


@router.get("/sessions")
async def list_sessions():
    """Return active session counts (diagnostics)."""
    return store.active_counts()
