"""
Hybrid Swarm Simulation service.

Pre-computes the full 3-drone trajectory and channel data for the
configured duration, then exposes frame-by-frame access for the API layer.

Extracted from hybrid_swarm_live_animation.py — no matplotlib dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .swarm_channel import (
    CELL_SINR_MIN,
    RF_SINR_MIN,
    compute_channel,
    frame_summary,
)

# ── Defaults (match hybrid_swarm_live_animation.py) ───────────────────────────

DEFAULT_N_DRONES    = 3
DEFAULT_TOTAL_TIME  = 120.0   # seconds
DEFAULT_DT          = 0.2     # seconds per step
DEFAULT_AREA_XY     = 1000.0  # metres
DEFAULT_MAX_ALT     = 150.0
DEFAULT_MIN_ALT     = 50.0
DEFAULT_BS          = (500.0, 500.0, 0.0)


# ── Data types returned by the API ────────────────────────────────────────────

@dataclass
class HybridDroneFrame:
    id: str
    pos: list[float]          # [x, y, z]
    cellular_sinr_db: float
    cellular_ok: bool
    rf_peers: int
    throughput_mbps: float


@dataclass
class HybridFrame:
    frame: int
    time_s: float
    drones: list[HybridDroneFrame]
    summary: dict


@dataclass
class HybridSimResult:
    """Holds the fully pre-computed simulation."""
    n_drones:  int
    steps:     int
    dt:        float
    total_time_s: float
    frames:    list[HybridFrame] = field(default_factory=list)

    def get_frame(self, k: int) -> HybridFrame | None:
        if 0 <= k < len(self.frames):
            return self.frames[k]
        return None


# ── Simulation class ──────────────────────────────────────────────────────────

class HybridSwarmSim:
    """
    Pre-computes drone trajectories + channel data for all timesteps.
    Call `run()` once, then use `result.get_frame(k)` or `result.frames`.
    """

    def __init__(
        self,
        n_drones:    int   = DEFAULT_N_DRONES,
        total_time_s: float = DEFAULT_TOTAL_TIME,
        dt:          float = DEFAULT_DT,
        area_xy:     float = DEFAULT_AREA_XY,
        max_alt:     float = DEFAULT_MAX_ALT,
        min_alt:     float = DEFAULT_MIN_ALT,
        bs:          tuple = DEFAULT_BS,
        seed:        int   = 42,
    ) -> None:
        self.n_drones     = n_drones
        self.total_time_s = total_time_s
        self.dt           = dt
        self.area_xy      = area_xy
        self.max_alt      = max_alt
        self.min_alt      = min_alt
        self.bs           = np.array(bs, dtype=float)
        self.rng          = np.random.default_rng(seed)

    def run(self) -> HybridSimResult:
        """Pre-compute full simulation and return a HybridSimResult."""
        t_vec = np.arange(0.0, self.total_time_s + self.dt, self.dt)
        steps = t_vec.size
        n     = self.n_drones
        rng   = self.rng

        # ── Trajectory ────────────────────────────────────────────────────────
        pos       = np.zeros((n, 3, steps), dtype=float)
        vel       = np.zeros((n, 3),        dtype=float)
        waypoints = np.zeros((n, 3),        dtype=float)

        for i in range(n):
            pos[i, :, 0] = [
                rng.uniform(0.0, self.area_xy),
                rng.uniform(0.0, self.area_xy),
                rng.uniform(self.min_alt, self.max_alt),
            ]
            waypoints[i] = [
                rng.uniform(0.0, self.area_xy),
                rng.uniform(0.0, self.area_xy),
                rng.uniform(self.min_alt, self.max_alt),
            ]
            spd       = rng.uniform(12.0, 20.0)
            direction = waypoints[i] - pos[i, :, 0]
            vel[i]    = direction / (np.linalg.norm(direction) + 1e-9) * spd

        for k in range(1, steps):
            for i in range(n):
                cur = pos[i, :, k - 1].copy()
                if np.linalg.norm(waypoints[i] - cur) < 25.0:
                    waypoints[i] = [
                        rng.uniform(0.0, self.area_xy),
                        rng.uniform(0.0, self.area_xy),
                        rng.uniform(self.min_alt, self.max_alt),
                    ]
                    spd       = rng.uniform(12.0, 20.0)
                    direction = waypoints[i] - cur
                    vel[i]    = direction / (np.linalg.norm(direction) + 1e-9) * spd

                nxt    = cur + vel[i] * self.dt
                nxt[0] = np.clip(nxt[0], 0.0, self.area_xy)
                nxt[1] = np.clip(nxt[1], 0.0, self.area_xy)
                nxt[2] = np.clip(nxt[2], self.min_alt, self.max_alt)
                pos[i, :, k] = nxt

        # ── Channel (all steps) ───────────────────────────────────────────────
        frames: list[HybridFrame] = []

        for k in range(steps):
            positions_k = pos[:, :, k]           # shape (n, 3)
            sinr_cell, sinr_rf, thr = compute_channel(
                positions_k, self.bs, rng, n_drones=n
            )

            drone_frames = []
            for i in range(n):
                p = pos[i, :, k]
                drone_frames.append(HybridDroneFrame(
                    id=f"D{i + 1}",
                    pos=[round(float(p[0]), 2), round(float(p[1]), 2), round(float(p[2]), 2)],
                    cellular_sinr_db=round(float(sinr_cell[i]), 2),
                    cellular_ok=bool(sinr_cell[i] >= CELL_SINR_MIN),
                    rf_peers=int(np.sum(sinr_rf[i] >= RF_SINR_MIN)),
                    throughput_mbps=round(float(thr[i]), 3),
                ))

            frames.append(HybridFrame(
                frame=k,
                time_s=round(float(t_vec[k]), 2),
                drones=drone_frames,
                summary=frame_summary(sinr_cell, sinr_rf, thr),
            ))

        return HybridSimResult(
            n_drones=n,
            steps=steps,
            dt=self.dt,
            total_time_s=self.total_time_s,
            frames=frames,
        )
