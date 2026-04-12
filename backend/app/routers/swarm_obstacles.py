"""
Swarm + Obstacle simulation router.

Endpoints
---------
POST   /api/v1/swarm/obstacles/start
    Create a new stateful simulation session.
    Returns session_id + configuration echo.

WS     /api/v1/swarm/obstacles/{session_id}/stream
    Stream live frames over a WebSocket — one frame per dt interval.
    Sends a "done" message when the simulation reaches total_time_s.

POST   /api/v1/swarm/obstacles/{session_id}/reset
    Reset simulation to t=0 (same parameters, new RNG state).

DELETE /api/v1/swarm/obstacles/{session_id}
    Destroy a session and free memory.
"""

import asyncio
import dataclasses
import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..services.swarm_obstacle_sim import (
    DEFAULT_ACTIVE_SENSORS,
    DEFAULT_END_POINTS,
    DEFAULT_FPS,
    DEFAULT_N_DRONES,
    DEFAULT_OBS_RADIUS_MAX,
    DEFAULT_OBS_RADIUS_MIN,
    DEFAULT_SPEEDS,
    DEFAULT_START_POINTS,
    DEFAULT_TOTAL_S,
    SwarmObstacleSim,
)
from ..services import sim_session_store as store
from ..services.sim_session_store import cache_obstacle_frame, get_obstacle_frame

router = APIRouter(prefix="/swarm/obstacles", tags=["swarm_obstacles"])


# ── Request / response schemas ────────────────────────────────────────────────

class StartRequest(BaseModel):
    n_drones:       int                    = Field(default=DEFAULT_N_DRONES, ge=1, le=6)
    # Accept as [[lat, lon, alt_m], ...] when ref_lat/ref_lon provided,
    # or as [[x_m, y_m, z_m], ...] in abstract space otherwise.
    start_points:   list[list[float]]      = Field(default=DEFAULT_START_POINTS)
    end_points:     list[list[float]]      = Field(default=DEFAULT_END_POINTS)
    speeds:         list[float]            = Field(default=DEFAULT_SPEEDS)
    active_sensors: dict[str, bool]        = Field(default=DEFAULT_ACTIVE_SENSORS)
    fps:            int                    = Field(default=DEFAULT_FPS, ge=1, le=60)
    total_time_s:   float                  = Field(default=DEFAULT_TOTAL_S, gt=0)
    seed:           int                    = Field(default=42)
    # Geo coordinates — set both to enable lat/lon mode
    ref_lat:        float | None           = Field(default=None)
    ref_lon:        float | None           = Field(default=None)
    # Obstacle size range (metres)
    obs_count:      int                    = Field(default=8, ge=0, le=30)
    obs_radius_min: float                  = Field(default=DEFAULT_OBS_RADIUS_MIN, gt=0)
    obs_radius_max: float                  = Field(default=DEFAULT_OBS_RADIUS_MAX, gt=0)


class StartResponse(BaseModel):
    session_id:   str
    n_drones:     int
    total_frames: int
    fps:          int
    total_time_s: float
    geo_mode:     bool   # True when lat/lon coordinates are active


# ── Helper ────────────────────────────────────────────────────────────────────

def _frame_to_dict(frame) -> dict:
    return dataclasses.asdict(frame)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/start", response_model=StartResponse)
async def start_simulation(body: StartRequest):
    """
    Create a new SwarmObstacleSim session.
    The simulation is stateful — each WebSocket connection advances it frame by frame.
    """
    sim = SwarmObstacleSim(
        n_drones=body.n_drones,
        start_points=body.start_points,
        end_points=body.end_points,
        speeds=body.speeds,
        active_sensors=body.active_sensors,
        fps=body.fps,
        total_time_s=body.total_time_s,
        initial_obs=body.obs_count,
        obs_radius_min=body.obs_radius_min,
        obs_radius_max=body.obs_radius_max,
        ref_lat=body.ref_lat,
        ref_lon=body.ref_lon,
        seed=body.seed,
    )
    sid = store.store_obstacle(sim)

    return StartResponse(
        session_id=sid,
        n_drones=sim.n_drones,
        total_frames=sim.total_frames,
        fps=body.fps,
        total_time_s=sim.total_time_s,
        geo_mode=body.ref_lat is not None,
    )


@router.websocket("/{session_id}/stream")
async def stream_simulation(websocket: WebSocket, session_id: str):
    """
    Stream live simulation frames over WebSocket.
    Calls sim.step() each interval, sending the resulting frame as JSON.
    Continues until sim.done or the client disconnects.
    """
    sim = store.get_obstacle(session_id)
    if sim is None:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    interval = sim.dt   # seconds between frames

    try:
        while not sim.done:
            frame = sim.step()
            frame_dict = _frame_to_dict(frame)
            cache_obstacle_frame(session_id, frame_dict)
            await websocket.send_text(json.dumps(frame_dict))
            await asyncio.sleep(interval)

        await websocket.send_json({
            "type": "done",
            "total_frames": sim.total_frames,
            "total_time_s": sim.total_time_s,
        })
        await websocket.close()

    except WebSocketDisconnect:
        pass   # client left — session stays in store for potential reconnect/reset


@router.get("/{session_id}/snapshot")
async def get_snapshot(session_id: str):
    """
    Return the most recently computed frame without advancing the simulation.
    Returns 404 before the first WebSocket frame has been produced.
    """
    frame = get_obstacle_frame(session_id)
    if frame is None:
        raise HTTPException(status_code=404, detail="No frame yet")
    return frame


@router.post("/{session_id}/reset")
async def reset_simulation(session_id: str):
    """Reset a simulation to t=0 (keeps same parameters)."""
    sim = store.get_obstacle(session_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Session not found")
    sim.reset()
    return {"reset": True, "session_id": session_id}


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Remove a session from memory."""
    removed = store.delete_obstacle(session_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": session_id}
