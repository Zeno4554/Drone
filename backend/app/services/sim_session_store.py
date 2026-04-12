"""
In-memory simulation session registry.

Stores running HybridSwarmSim results and SwarmObstacleSim instances,
keyed by a UUID session_id. Sessions are cleaned up on WebSocket disconnect.
"""

from __future__ import annotations

import uuid
from typing import Union

from .hybrid_swarm_sim import HybridSimResult
from .swarm_obstacle_sim import SwarmObstacleSim

_SimObject = Union[HybridSimResult, SwarmObstacleSim]

# Module-level stores (one dict per simulation type)
_hybrid_sessions:   dict[str, HybridSimResult]  = {}
_obstacle_sessions: dict[str, SwarmObstacleSim] = {}
_obstacle_frames:   dict[str, dict]              = {}   # latest frame cache


# ── Hybrid sessions ───────────────────────────────────────────────────────────

def store_hybrid(result: HybridSimResult) -> str:
    """Store a pre-computed hybrid simulation result. Returns a new session_id."""
    session_id = str(uuid.uuid4())
    _hybrid_sessions[session_id] = result
    return session_id


def get_hybrid(session_id: str) -> HybridSimResult | None:
    return _hybrid_sessions.get(session_id)


def delete_hybrid(session_id: str) -> bool:
    return _hybrid_sessions.pop(session_id, None) is not None


# ── Obstacle sessions ─────────────────────────────────────────────────────────

def store_obstacle(sim: SwarmObstacleSim) -> str:
    """Store a SwarmObstacleSim instance. Returns a new session_id."""
    session_id = str(uuid.uuid4())
    _obstacle_sessions[session_id] = sim
    return session_id


def get_obstacle(session_id: str) -> SwarmObstacleSim | None:
    return _obstacle_sessions.get(session_id)


def delete_obstacle(session_id: str) -> bool:
    _obstacle_frames.pop(session_id, None)
    return _obstacle_sessions.pop(session_id, None) is not None


def cache_obstacle_frame(session_id: str, frame: dict) -> None:
    """Cache the most recently computed frame for a session."""
    _obstacle_frames[session_id] = frame


def get_obstacle_frame(session_id: str) -> dict | None:
    """Return the latest cached frame, or None if none yet."""
    return _obstacle_frames.get(session_id)


# ── Diagnostics ───────────────────────────────────────────────────────────────

def active_counts() -> dict[str, int]:
    return {
        "hybrid_sessions":   len(_hybrid_sessions),
        "obstacle_sessions": len(_obstacle_sessions),
    }
