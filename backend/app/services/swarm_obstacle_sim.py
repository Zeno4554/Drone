"""
Swarm + Obstacle Simulation service.

Stateful, per-frame simulation: drones move from fixed start → end points
while dynamic obstacles spawn/despawn and sensors cast rays each step.

Changes vs. original:
  - Obstacles now carry individual radii (variable sizes).
  - Accepts lat/lon start/end points via coord_utils when ref_lat/ref_lon provided.
  - Each streamed frame includes pos_ll [lat, lon, alt_m] alongside pos [x,y,z].
  - Obstacle list in frames includes radius per entry.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .swarm_channel import (
    CELL_SINR_MIN,
    RF_SINR_MIN,
    compute_channel,
    frame_summary,
)
from .coord_utils import build_coord_mapper, centroid

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_N_DRONES  = 4
DEFAULT_FPS       = 20
DEFAULT_TOTAL_S   = 120.0
DEFAULT_AREA_XY   = 1000.0
DEFAULT_MAX_ALT   = 150.0
DEFAULT_MIN_ALT   = 20.0
DEFAULT_BS        = (500.0, 500.0, 0.0)

DEFAULT_START_POINTS = [
    [100.0, 150.0,  60.0],
    [180.0, 820.0,  95.0],
    [880.0, 140.0, 120.0],
    [900.0, 860.0,  80.0],
]
DEFAULT_END_POINTS = [
    [860.0, 780.0, 110.0],
    [820.0, 200.0,  65.0],
    [180.0, 760.0,  85.0],
    [120.0, 220.0, 130.0],
]
DEFAULT_SPEEDS = [14.0, 17.0, 16.0, 15.0]

DEFAULT_ACTIVE_SENSORS  = {"ultrasonic": True, "lidar": True, "radar": True}
DEFAULT_ULTRASONIC_RANGE = 80.0
DEFAULT_LIDAR_RAYS       = 24
DEFAULT_LIDAR_RANGE      = 150.0
DEFAULT_RADAR_RANGE      = 220.0
DEFAULT_NOISE_STD        = 1.0

# Obstacle defaults
DEFAULT_INITIAL_OBS    = 8
DEFAULT_MAX_OBS        = 24
DEFAULT_SPAWN_PROB     = 0.04
DEFAULT_DESPAWN_PROB   = 0.02
DEFAULT_OBS_RADIUS_MIN = 5.0    # metres
DEFAULT_OBS_RADIUS_MAX = 30.0   # metres

ARRIVAL_EPS = 8.0


# ── Internal types ────────────────────────────────────────────────────────────

@dataclass
class _DroneState:
    pos:     np.ndarray   # [x, y, z] in sim metres
    end:     np.ndarray
    speed:   float
    arrived: bool = False


@dataclass
class _Obstacle:
    pos:    np.ndarray   # [x, y, z] in sim metres
    radius: float        # metres


# ── Output data types ─────────────────────────────────────────────────────────

@dataclass
class SensorReading:
    ultrasonic_m:  float | None
    lidar_rays_m:  list[float] | None
    radar_range_m: float | None


@dataclass
class ObstacleDroneFrame:
    id:                 str
    pos:                list[float]        # [x, y, z] sim metres
    pos_ll:             list[float] | None # [lat, lon, alt_m] — None if no ref
    arrived:            bool
    cellular_sinr_db:   float
    cellular_ok:        bool
    rf_peers:           int
    throughput_mbps:    float
    nearest_obstacle_m: float
    sensors:            SensorReading


@dataclass
class ObstacleEntry:
    pos:    list[float]   # [x, y, z]
    pos_ll: list[float] | None
    radius: float


@dataclass
class ObstacleFrame:
    frame:     int
    time_s:    float
    drones:    list[ObstacleDroneFrame]
    obstacles: list[ObstacleEntry]
    summary:   dict


# ── Simulation class ──────────────────────────────────────────────────────────

class SwarmObstacleSim:
    """
    Stateful per-frame simulation.
    Call step() each frame to advance. Thread-safe only for a single async driver.
    """

    def __init__(
        self,
        n_drones:        int                      = DEFAULT_N_DRONES,
        start_points:    list[list[float]] | None = None,
        end_points:      list[list[float]] | None = None,
        speeds:          list[float]       | None = None,
        active_sensors:  dict[str, bool]   | None = None,
        area_xy:         float = DEFAULT_AREA_XY,
        max_alt:         float = DEFAULT_MAX_ALT,
        min_alt:         float = DEFAULT_MIN_ALT,
        bs:              tuple = DEFAULT_BS,
        fps:             int   = DEFAULT_FPS,
        total_time_s:    float = DEFAULT_TOTAL_S,
        initial_obs:     int   = DEFAULT_INITIAL_OBS,
        max_obs:         int   = DEFAULT_MAX_OBS,
        spawn_prob:      float = DEFAULT_SPAWN_PROB,
        despawn_prob:    float = DEFAULT_DESPAWN_PROB,
        obs_radius_min:  float = DEFAULT_OBS_RADIUS_MIN,
        obs_radius_max:  float = DEFAULT_OBS_RADIUS_MAX,
        noise_std:       float = DEFAULT_NOISE_STD,
        lidar_rays:      int   = DEFAULT_LIDAR_RAYS,
        # Geo support — if provided, start/end are [lat, lon, alt_m]
        ref_lat:         float | None = None,
        ref_lon:         float | None = None,
        seed:            int   = 42,
    ) -> None:
        self.n_drones       = n_drones
        self.area_xy        = area_xy
        self.max_alt        = max_alt
        self.min_alt        = min_alt
        self.bs             = np.array(bs, dtype=float)
        self.dt             = 1.0 / fps
        self.total_time_s   = total_time_s
        self.total_frames   = int(total_time_s * fps)
        self.initial_obs    = initial_obs
        self.max_obs        = max_obs
        self.spawn_prob     = spawn_prob
        self.despawn_prob   = despawn_prob
        self.obs_radius_min = obs_radius_min
        self.obs_radius_max = obs_radius_max
        self.noise_std      = noise_std
        self.lidar_rays     = lidar_rays
        self.active_sensors = active_sensors or dict(DEFAULT_ACTIVE_SENSORS)
        self._seed          = seed
        self.ref_lat        = ref_lat
        self.ref_lon        = ref_lon
        self._to_sim        = None
        self._from_sim      = None

        # Clamp to n_drones
        sp = (start_points or DEFAULT_START_POINTS)[:n_drones]
        ep = (end_points   or DEFAULT_END_POINTS)[:n_drones]
        sv = (speeds       or DEFAULT_SPEEDS)[:n_drones]

        # Build coordinate mapper if geo coords provided
        if ref_lat is not None and ref_lon is not None:
            self._to_sim, self._from_sim = build_coord_mapper(
                ref_lat, ref_lon,
                ref_x_offset=area_xy / 2,
                ref_y_offset=area_xy / 2,
            )
            # Convert lat/lon/alt → sim x/y, keep alt
            self._start_m = [
                np.array([*self._to_sim(p[0], p[1]), float(p[2])], dtype=float)
                for p in sp
            ]
            self._end_m = [
                np.array([*self._to_sim(p[0], p[1]), float(p[2])], dtype=float)
                for p in ep
            ]
        else:
            self._start_m = [np.array(p, dtype=float) for p in sp]
            self._end_m   = [np.array(p, dtype=float) for p in ep]

        self._speeds = list(sv)
        self._init_state()

    # ── State ─────────────────────────────────────────────────────────────────

    def _init_state(self) -> None:
        self.rng    = np.random.default_rng(self._seed)
        self.frame  = 0
        self.drones = [
            _DroneState(
                pos=self._start_m[i].copy(),
                end=self._end_m[i].copy(),
                speed=float(self._speeds[i]),
            )
            for i in range(self.n_drones)
        ]
        self.obstacles: list[_Obstacle] = [
            self._random_obstacle() for _ in range(self.initial_obs)
        ]

    def reset(self) -> None:
        self._init_state()

    @property
    def done(self) -> bool:
        return self.frame >= self.total_frames

    # ── Obstacle helpers ──────────────────────────────────────────────────────

    def _random_obstacle(self) -> _Obstacle:
        return _Obstacle(
            pos=np.array([
                self.rng.uniform(40.0, self.area_xy - 40.0),
                self.rng.uniform(40.0, self.area_xy - 40.0),
                self.rng.uniform(self.min_alt, self.max_alt),
            ], dtype=float),
            radius=float(self.rng.uniform(self.obs_radius_min, self.obs_radius_max)),
        )

    def _manage_obstacles(self) -> None:
        if self.rng.random() < self.spawn_prob and len(self.obstacles) < self.max_obs:
            # Try a few times to spawn an obstacle that isn't on top of a drone
            for _ in range(5):
                new_obs = self._random_obstacle()
                safe = True
                for drone in self.drones:
                    if np.linalg.norm(new_obs.pos - drone.pos) < new_obs.radius + 15.0:
                        safe = False
                        break
                if safe:
                    self.obstacles.append(new_obs)
                    break
                    
        if self.rng.random() < self.despawn_prob and len(self.obstacles) > self.initial_obs:
            self.obstacles.pop(0)

    # ── Ray casting ───────────────────────────────────────────────────────────

    def _cast_ray(self, origin: np.ndarray, direction: np.ndarray, max_range: float) -> float:
        step = 2.0
        dist = 0.0
        d    = direction / (np.linalg.norm(direction) + 1e-9)

        while dist < max_range:
            dist += step
            probe = origin + d * dist
            x, y, z = probe

            if not (0.0 <= x <= self.area_xy
                    and 0.0 <= y <= self.area_xy
                    and self.min_alt <= z <= self.max_alt):
                dist = max(0.0, dist - step)
                break

            if any(np.linalg.norm(probe - o.pos) < o.radius for o in self.obstacles):
                dist = max(0.0, dist - step)
                break

        return max(0.0, dist + self.rng.normal(0.0, self.noise_std))

    # ── Sensors ───────────────────────────────────────────────────────────────

    def _sense(self, drone: _DroneState) -> SensorReading:
        p = drone.pos
        goal_vec = drone.end - p
        norm = np.linalg.norm(goal_vec)
        if norm > 1e-6:
            fwd = goal_vec / norm
        else:
            yaw = 2.0 * np.pi * (self.frame % 360) / 360.0
            fwd = np.array([math.cos(yaw), math.sin(yaw), 0.0])

        us = None
        if self.active_sensors.get("ultrasonic"):
            us = round(self._cast_ray(p, fwd, DEFAULT_ULTRASONIC_RANGE), 2)

        lidar = None
        if self.active_sensors.get("lidar"):
            lidar = []
            for r in range(self.lidar_rays):
                angle   = 2.0 * np.pi * r / self.lidar_rays
                ray_dir = np.array([math.cos(angle), math.sin(angle), 0.0])
                lidar.append(round(self._cast_ray(p, ray_dir, DEFAULT_LIDAR_RANGE), 2))

        radar = DEFAULT_RADAR_RANGE if self.active_sensors.get("radar") else None

        return SensorReading(ultrasonic_m=us, lidar_rays_m=lidar, radar_range_m=radar)

    # ── Coordinate helpers ────────────────────────────────────────────────────

    def _pos_ll(self, pos: np.ndarray) -> list[float] | None:
        """Convert sim [x,y,z] → [lat, lon, alt_m]. None if no ref set."""
        if self._from_sim is None:
            return None
        lat, lon = self._from_sim(float(pos[0]), float(pos[1]))
        return [round(lat, 6), round(lon, 6), round(float(pos[2]), 1)]

    # ── Step ──────────────────────────────────────────────────────────────────

    def step(self) -> ObstacleFrame:
        """Advance one frame and return serialisable frame data."""
        # Move drones
        for i, drone in enumerate(self.drones):
            if drone.arrived:
                continue
            
            # Simple reactive collision avoidance (Boids-like separation)
            repulsion = np.zeros(3)
            # 1. Dodge other drones
            for j, other in enumerate(self.drones):
                if i == j: continue
                diff = drone.pos - other.pos
                dist = np.linalg.norm(diff)
                if dist < 20.0 and dist > 0.1: # 20m safety radius
                    repulsion += (diff / dist) * (20.0 - dist) * 2.0
                    
            # 2. Dodge obstacles
            for obs in self.obstacles:
                diff = drone.pos - obs.pos
                dist = np.linalg.norm(diff)
                safe_dist = obs.radius + 15.0 # 15m buffer around obstacles
                if dist < safe_dist:
                    # Exponential push away so it can never enter
                    intensity = 5.0 * np.exp(3.0 * (1.0 - (dist / safe_dist)))
                    repulsion += (diff / (dist + 1e-9)) * intensity
            
            to_goal = drone.end - drone.pos
            dist    = np.linalg.norm(to_goal)
            
            if dist <= ARRIVAL_EPS:
                drone.pos     = drone.end.copy()
                drone.arrived = True
            else:
                # Combine goal direction with repulsion
                direction = (to_goal / (dist + 1e-9)) * drone.speed
                velocity = direction + repulsion
                
                # Normalize actual step to respect max speed
                actual_speed = np.linalg.norm(velocity)
                if actual_speed > 1e-6:
                    velocity = (velocity / actual_speed) * drone.speed
                
                step_dist = min(np.linalg.norm(velocity) * self.dt, dist)
                if step_dist > 1e-6:
                    step_dir = velocity / np.linalg.norm(velocity)
                    drone.pos = drone.pos + step_dir * step_dist
                
                drone.pos[0] = np.clip(drone.pos[0], 0.0, self.area_xy)
                drone.pos[1] = np.clip(drone.pos[1], 0.0, self.area_xy)
                drone.pos[2] = np.clip(drone.pos[2], self.min_alt, self.max_alt)

        # Obstacle lifecycle
        self._manage_obstacles()

        # Channel
        positions = np.vstack([d.pos for d in self.drones])
        sinr_cell, sinr_rf, thr = compute_channel(
            positions, self.bs, self.rng, n_drones=self.n_drones
        )

        # Per-drone output
        drone_frames: list[ObstacleDroneFrame] = []
        for i, drone in enumerate(self.drones):
            p = drone.pos
            nearest = (
                float(min(np.linalg.norm(p - o.pos) - o.radius for o in self.obstacles))
                if self.obstacles else float("inf")
            )
            drone_frames.append(ObstacleDroneFrame(
                id=f"D{i + 1}",
                pos=[round(float(p[0]), 2), round(float(p[1]), 2), round(float(p[2]), 2)],
                pos_ll=self._pos_ll(p),
                arrived=drone.arrived,
                cellular_sinr_db=round(float(sinr_cell[i]), 2),
                cellular_ok=bool(sinr_cell[i] >= CELL_SINR_MIN),
                rf_peers=int(np.sum(sinr_rf[i] >= RF_SINR_MIN)),
                throughput_mbps=round(float(thr[i]), 3),
                nearest_obstacle_m=round(max(nearest, 0.0), 2) if nearest != float("inf") else -1.0,
                sensors=self._sense(drone),
            ))

        # Obstacle output (with radius + optional lat/lon)
        obs_entries: list[ObstacleEntry] = [
            ObstacleEntry(
                pos=[round(float(o.pos[0]), 1), round(float(o.pos[1]), 1), round(float(o.pos[2]), 1)],
                pos_ll=self._pos_ll(o.pos),
                radius=round(o.radius, 1),
            )
            for o in self.obstacles
        ]

        # RF link pairs for visualisation
        rf_pairs = [
            [i, j]
            for i in range(self.n_drones)
            for j in range(i + 1, self.n_drones)
            if sinr_rf[i, j] >= RF_SINR_MIN
        ]

        summary = frame_summary(sinr_cell, sinr_rf, thr)
        summary["total_obstacles"] = len(self.obstacles)
        summary["arrived"]         = sum(d.arrived for d in self.drones)
        summary["rf_pairs"]        = rf_pairs

        result = ObstacleFrame(
            frame=self.frame,
            time_s=round(self.frame * self.dt, 2),
            drones=drone_frames,
            obstacles=obs_entries,
            summary=summary,
        )

        self.frame += 1
        return result
