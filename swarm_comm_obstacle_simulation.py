"""
Swarm Communication + Obstacle Sensing (3D)
===========================================
Combined simulation with:
- Multiple drones moving from fixed start points to fixed end points
- Cellular links to a base station + RF drone-to-drone links
- Dynamic obstacles and per-drone sensors (ultrasonic, LiDAR, radar)

This combines the general behavior of:
- drone_simulation.py (obstacles + sensors)
- hybrid_swarm_live_animation.py (swarm communications)
"""

import math
from dataclasses import dataclass

import matplotlib.animation as animation
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np


# ============================================================
# USER CONFIGURATION
# ============================================================
N_DRONES = 6
FPS = 20
DT = 1.0 / FPS
TOTAL_TIME_S = 120.0
AREA_XY = 1000.0
MAX_ALT = 150.0
MIN_ALT = 20.0

# Base station
BS = np.array([500.0, 500.0, 0.0], dtype=float)

# Hardcoded start and end locations (x, y, z)
START_POINTS = np.array(
    [
        [100.0, 150.0, 60.0],
        [180.0, 820.0, 95.0],
        [880.0, 140.0, 120.0],
        [900.0, 860.0, 80.0],
        [300.0, 500.0, 70.0],
        [650.0, 320.0, 110.0],
    ],
    dtype=float,
)

END_POINTS = np.array(
    [
        [860.0, 780.0, 110.0],
        [820.0, 200.0, 65.0],
        [180.0, 760.0, 85.0],
        [120.0, 220.0, 130.0],
        [760.0, 540.0, 120.0],
        [320.0, 860.0, 75.0],
    ],
    dtype=float,
)

# Drone nominal speeds (m/s), one per drone
DRONE_SPEEDS = np.array([14.0, 17.0, 16.0, 15.0, 18.0, 13.0], dtype=float)
ARRIVAL_EPS = 8.0

# Sensor toggles
ACTIVE_SENSORS = {
    "ultrasonic": True,
    "lidar": True,
    "radar": True,
}

# Sensor parameters
ULTRASONIC_RANGE = 80.0
LIDAR_RAYS = 24
LIDAR_RANGE = 150.0
RADAR_RANGE = 220.0
NOISE_STD = 1.0
OBSTACLE_RADIUS = 14.0

# Dynamic obstacle settings
INITIAL_OBSTACLES = 8
MAX_OBSTACLES = 24
SPAWN_PROBABILITY = 0.04
DESPAWN_PROBABILITY = 0.02

# Communication/channel model
F_CELL = 2.4e9
PT_UE_DBM = 23.0
NF_CELL_DB = 7.0
BW_CELL_HZ = 10e6
N_CELL = 3.5
D0_CELL = 100.0
SINR_MIN_CELL_DB = 5.0

F_RF = 915e6
PT_RF_DBM = 20.0
NF_RF_DB = 5.0
BW_RF_HZ = 1e6
N_RF = 2.2
D0_RF = 10.0
RF_RANGE = 400.0
SINR_MIN_RF_DB = 3.0

C = 3e8
K_B = 1.38e-23
T_NOISE = 290.0

PL0_CELL_DB = 20.0 * np.log10(4.0 * np.pi * D0_CELL * F_CELL / C)
PL0_RF_DB = 20.0 * np.log10(4.0 * np.pi * D0_RF * F_RF / C)
N0_CELL_DBM = 10.0 * np.log10(K_B * T_NOISE * BW_CELL_HZ) + 30.0 + NF_CELL_DB
N0_RF_DBM = 10.0 * np.log10(K_B * T_NOISE * BW_RF_HZ) + 30.0 + NF_RF_DB

TRAIL_LEN = 50


@dataclass
class DroneState:
    pos: np.ndarray
    end: np.ndarray
    speed: float
    arrived: bool = False


def _random_obstacle(rng: np.random.Generator) -> np.ndarray:
    return np.array(
        [
            rng.uniform(40.0, AREA_XY - 40.0),
            rng.uniform(40.0, AREA_XY - 40.0),
            rng.uniform(MIN_ALT, MAX_ALT),
        ],
        dtype=float,
    )


def maybe_spawn_obstacle(obstacles: list[np.ndarray], rng: np.random.Generator) -> None:
    if rng.random() < SPAWN_PROBABILITY and len(obstacles) < MAX_OBSTACLES:
        obstacles.append(_random_obstacle(rng))


def maybe_despawn_obstacle(obstacles: list[np.ndarray], rng: np.random.Generator) -> None:
    if rng.random() < DESPAWN_PROBABILITY and len(obstacles) > INITIAL_OBSTACLES:
        obstacles.pop(0)


def cast_ray(
    origin: np.ndarray,
    direction: np.ndarray,
    max_range: float,
    obstacles: list[np.ndarray],
    rng: np.random.Generator,
) -> float:
    """March a ray and return hit distance to wall/obstacle with Gaussian noise."""
    step = 2.0
    dist = 0.0
    d = direction / (np.linalg.norm(direction) + 1e-9)

    while dist < max_range:
        dist += step
        probe = origin + d * dist
        x, y, z = probe

        out_of_bounds = not (0.0 <= x <= AREA_XY and 0.0 <= y <= AREA_XY and MIN_ALT <= z <= MAX_ALT)
        if out_of_bounds:
            dist = max(0.0, dist - step)
            break

        hit = any(np.linalg.norm(probe - o) < OBSTACLE_RADIUS for o in obstacles)
        if hit:
            dist = max(0.0, dist - step)
            break

    return max(0.0, dist + rng.normal(0.0, NOISE_STD))


def circle_3d(cx: float, cy: float, cz: float, r: float, n: int = 72) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    angles = np.linspace(0.0, 2.0 * np.pi, n + 1)
    xs = cx + r * np.cos(angles)
    ys = cy + r * np.sin(angles)
    zs = np.full_like(xs, cz)
    return xs, ys, zs


def compute_channel(
    positions: np.ndarray,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute current cellular SINR, RF SINR matrix, and hybrid throughput."""
    sinr_cell = np.zeros(N_DRONES, dtype=float)
    sinr_rf = np.full((N_DRONES, N_DRONES), -np.inf, dtype=float)
    c_cell = np.zeros(N_DRONES, dtype=float)
    best_rf = np.zeros(N_DRONES, dtype=float)

    for i in range(N_DRONES):
        p_i = positions[i]
        d_bs = np.linalg.norm(p_i - BS)
        pl_c = PL0_CELL_DB + 10.0 * N_CELL * np.log10(max(d_bs, D0_CELL) / D0_CELL) + 6.0 * rng.normal()
        sinr_cell[i] = PT_UE_DBM - pl_c - N0_CELL_DBM
        if sinr_cell[i] >= SINR_MIN_CELL_DB:
            c_cell[i] = BW_CELL_HZ * np.log2(1.0 + 10.0 ** (sinr_cell[i] / 10.0)) / 1e6

    for i in range(N_DRONES):
        for j in range(i + 1, N_DRONES):
            d_ij = np.linalg.norm(positions[i] - positions[j])
            if d_ij < RF_RANGE:
                pl_r = PL0_RF_DB + 10.0 * N_RF * np.log10(max(d_ij, D0_RF) / D0_RF) + 2.0 * rng.normal()
                sinr_ij = PT_RF_DBM - pl_r - N0_RF_DBM
                sinr_rf[i, j] = sinr_ij
                sinr_rf[j, i] = sinr_ij
                if sinr_ij >= SINR_MIN_RF_DB:
                    c_rf = BW_RF_HZ * np.log2(1.0 + 10.0 ** (sinr_ij / 10.0)) / 1e6
                    best_rf[i] = max(best_rf[i], c_rf)
                    best_rf[j] = max(best_rf[j], c_rf)

    thr = c_cell + best_rf
    return sinr_cell, sinr_rf, thr


def main() -> None:
    rng = np.random.default_rng(42)

    if START_POINTS.shape != (N_DRONES, 3) or END_POINTS.shape != (N_DRONES, 3):
        raise ValueError("START_POINTS and END_POINTS must have shape (N_DRONES, 3)")

    drones = [
        DroneState(pos=START_POINTS[i].copy(), end=END_POINTS[i].copy(), speed=float(DRONE_SPEEDS[i]))
        for i in range(N_DRONES)
    ]

    obstacles = [_random_obstacle(rng) for _ in range(INITIAL_OBSTACLES)]

    colors = plt.get_cmap("tab10")(np.linspace(0.0, 1.0, N_DRONES))
    drone_names = [f"D{i + 1}" for i in range(N_DRONES)]

    plt.style.use("dark_background")
    fig = plt.figure(figsize=(15, 8.5), facecolor="#111822")
    fig.canvas.manager.set_window_title("Swarm Communication + Obstacle Sensing")

    # Main 3D view
    ax3d = fig.add_axes([0.02, 0.14, 0.70, 0.84], projection="3d", facecolor="#0b111c")
    ax3d.set_xlim(0.0, AREA_XY)
    ax3d.set_ylim(0.0, AREA_XY)
    ax3d.set_zlim(0.0, MAX_ALT + 20.0)
    ax3d.set_xlabel("X (m)")
    ax3d.set_ylabel("Y (m)")
    ax3d.set_zlabel("Altitude (m)")
    ax3d.set_title("[ SWARM COMMUNICATION + OBSTACLE SENSING ]", color="cyan", fontsize=12, fontweight="bold")
    ax3d.grid(True, alpha=0.35)
    ax3d.view_init(elev=28.0, azim=42.0)

    # Base station + start/end markers
    ax3d.scatter([BS[0]], [BS[1]], [BS[2]], s=260, c="red", marker="P", zorder=8)
    ax3d.text(BS[0] + 16.0, BS[1] + 16.0, BS[2] + 8.0, "gNB", color="#ff6f6f", fontsize=10, fontweight="bold")

    start_sc = ax3d.scatter(START_POINTS[:, 0], START_POINTS[:, 1], START_POINTS[:, 2], s=70, c="#44aaff", marker="^")
    end_sc = ax3d.scatter(END_POINTS[:, 0], END_POINTS[:, 1], END_POINTS[:, 2], s=70, c="#ffcc44", marker="X")
    _ = start_sc, end_sc

    # Obstacles
    obs_scatter = ax3d.scatter([], [], [], c="#ff4444", s=58, marker="s", depthshade=True, zorder=6)

    # Drone visuals
    trails = []
    drone_markers = []
    labels = []
    cell_links = []
    rf_links = [[None for _ in range(N_DRONES)] for _ in range(N_DRONES)]

    # Sensor visuals per drone
    us_lines = []
    lidar_lines = []
    radar_lines = []

    history = [np.array([d.pos.copy()]) for d in drones]

    for i in range(N_DRONES):
        tr, = ax3d.plot([], [], [], lw=1.2, color=(*colors[i, :3], 0.30))
        dm = ax3d.scatter([], [], [], s=110, c=[colors[i, :3]], marker="D", zorder=10)
        lb = ax3d.text(0.0, 0.0, 0.0, drone_names[i], color=colors[i, :3], fontsize=9, fontweight="bold")
        cl, = ax3d.plot([], [], [], "--", lw=1.4, color=(0.30, 0.55, 1.0, 0.70), zorder=5)

        trails.append(tr)
        drone_markers.append(dm)
        labels.append(lb)
        cell_links.append(cl)

        # Ultrasonic line per drone
        ul, = ax3d.plot([], [], [], "-", lw=2.0, color="#ffdd00", alpha=0.9, zorder=7)
        us_lines.append(ul)

        # LiDAR rays per drone
        rays_i = [
            ax3d.plot([], [], [], "-", lw=0.6, color="#33ff77", alpha=0.45, zorder=7)[0]
            for _ in range(LIDAR_RAYS)
        ]
        lidar_lines.append(rays_i)

        # Radar circle per drone
        rl, = ax3d.plot([], [], [], "-", lw=1.0, color="#4488ff", alpha=0.23, zorder=4)
        radar_lines.append(rl)

        for j in range(N_DRONES):
            link, = ax3d.plot([], [], [], "-", lw=2.0, color=(0.15, 1.0, 0.35, 0.8), zorder=5)
            rf_links[i][j] = link

    # Status panel
    ax_status = fig.add_axes([0.02, 0.02, 0.70, 0.11], facecolor="#0b111c")
    ax_status.axis("off")
    status_text = ax_status.text(
        0.01,
        0.58,
        "",
        transform=ax_status.transAxes,
        ha="left",
        va="center",
        fontsize=8.2,
        family="monospace",
        color="#d8f1d8",
    )

    # Right info panel
    ax_info = fig.add_axes([0.74, 0.14, 0.25, 0.84], facecolor="#0b111c")
    ax_info.axis("off")

    time_text = ax_info.text(
        0.50,
        0.95,
        "t = 0.0 s",
        ha="center",
        va="center",
        color="cyan",
        fontsize=14,
        fontweight="bold",
        family="monospace",
    )

    summary_text = ax_info.text(
        0.03,
        0.79,
        "",
        ha="left",
        va="top",
        color="#f6f0d2",
        fontsize=9.5,
        family="monospace",
        linespacing=1.35,
    )

    legend_handles = [
        mpatches.Patch(color="#ff4444", label="Dynamic Obstacle"),
        mpatches.Patch(color="#ffdd00", label="Ultrasonic"),
        mpatches.Patch(color="#33ff77", label="LiDAR"),
        mpatches.Patch(color="#4488ff", label="Radar"),
        mpatches.Patch(color="#2f8dff", label="Cellular Link"),
        mpatches.Patch(color="#26dd66", label="RF D2D Link"),
    ]
    ax_info.legend(
        handles=legend_handles,
        loc="lower left",
        facecolor="#111122",
        edgecolor="#334466",
        labelcolor="#d0d0e0",
        fontsize=9,
    )

    total_frames = int(TOTAL_TIME_S * FPS)

    def update(frame_idx: int):
        # Move each drone from start to end and hold position after arrival.
        for i, d in enumerate(drones):
            if not d.arrived:
                to_goal = d.end - d.pos
                dist = np.linalg.norm(to_goal)
                if dist <= ARRIVAL_EPS:
                    d.pos = d.end.copy()
                    d.arrived = True
                else:
                    direction = to_goal / (dist + 1e-9)
                    step = min(d.speed * DT, dist)
                    d.pos = d.pos + direction * step
                    d.pos[0] = np.clip(d.pos[0], 0.0, AREA_XY)
                    d.pos[1] = np.clip(d.pos[1], 0.0, AREA_XY)
                    d.pos[2] = np.clip(d.pos[2], MIN_ALT, MAX_ALT)

            history[i] = np.vstack((history[i], d.pos.copy()))
            if history[i].shape[0] > TRAIL_LEN:
                history[i] = history[i][-TRAIL_LEN:]

        # Dynamic obstacles
        maybe_spawn_obstacle(obstacles, rng)
        maybe_despawn_obstacle(obstacles, rng)

        if obstacles:
            obs_arr = np.vstack(obstacles)
            obs_scatter._offsets3d = (obs_arr[:, 0], obs_arr[:, 1], obs_arr[:, 2])
        else:
            obs_scatter._offsets3d = ([], [], [])

        positions = np.vstack([d.pos for d in drones])
        sinr_cell, sinr_rf, thr = compute_channel(positions, rng)

        # Per-drone visuals + sensing
        nearest_obs_dist = []
        for i, d in enumerate(drones):
            p = d.pos
            tr = history[i]

            trails[i].set_data(tr[:, 0], tr[:, 1])
            trails[i].set_3d_properties(tr[:, 2])

            drone_markers[i]._offsets3d = ([p[0]], [p[1]], [p[2]])
            labels[i].set_position((p[0] + 12.0, p[1] + 12.0))
            labels[i].set_3d_properties(p[2] + 6.0)

            # Cellular link color based on SINR threshold.
            if sinr_cell[i] >= SINR_MIN_CELL_DB:
                cell_color = (0.30, 0.55, 1.0, 0.70)
            else:
                cell_color = (1.0, 0.25, 0.25, 0.40)
            cell_links[i].set_data([p[0], BS[0]], [p[1], BS[1]])
            cell_links[i].set_3d_properties([p[2], BS[2]])
            cell_links[i].set_color(cell_color)

            # Heading uses goal direction until arrival, then yaw-only fallback.
            goal_vec = d.end - p
            if np.linalg.norm(goal_vec) > 1e-6:
                fwd = goal_vec / np.linalg.norm(goal_vec)
            else:
                yaw = 2.0 * np.pi * ((frame_idx + i * 11) % 360) / 360.0
                fwd = np.array([math.cos(yaw), math.sin(yaw), 0.0], dtype=float)

            # Ultrasonic forward beam
            if ACTIVE_SENSORS["ultrasonic"]:
                d_us = cast_ray(p, fwd, ULTRASONIC_RANGE, obstacles, rng)
                us_tip = p + fwd * d_us
                us_lines[i].set_data([p[0], us_tip[0]], [p[1], us_tip[1]])
                us_lines[i].set_3d_properties([p[2], us_tip[2]])
                us_lines[i].set_visible(True)
            else:
                us_lines[i].set_visible(False)

            # LiDAR rays (horizontal fan)
            for r_idx, line in enumerate(lidar_lines[i]):
                if ACTIVE_SENSORS["lidar"]:
                    angle = 2.0 * np.pi * r_idx / LIDAR_RAYS
                    ray_dir = np.array([math.cos(angle), math.sin(angle), 0.0], dtype=float)
                    d_l = cast_ray(p, ray_dir, LIDAR_RANGE, obstacles, rng)
                    tip = p + ray_dir * d_l
                    line.set_data([p[0], tip[0]], [p[1], tip[1]])
                    line.set_3d_properties([p[2], tip[2]])
                    line.set_visible(True)
                else:
                    line.set_visible(False)

            # Radar ring
            if ACTIVE_SENSORS["radar"]:
                rx, ry, rz = circle_3d(p[0], p[1], p[2], RADAR_RANGE)
                radar_lines[i].set_data(rx, ry)
                radar_lines[i].set_3d_properties(rz)
                radar_lines[i].set_visible(True)
            else:
                radar_lines[i].set_visible(False)

            if obstacles:
                dmin = float(min(np.linalg.norm(p - o) for o in obstacles))
            else:
                dmin = float("inf")
            nearest_obs_dist.append(dmin)

        # RF links between drones
        for i in range(N_DRONES):
            for j in range(i + 1, N_DRONES):
                if sinr_rf[i, j] >= SINR_MIN_RF_DB:
                    rf_links[i][j].set_data([positions[i, 0], positions[j, 0]], [positions[i, 1], positions[j, 1]])
                    rf_links[i][j].set_3d_properties([positions[i, 2], positions[j, 2]])
                else:
                    rf_links[i][j].set_data([], [])
                    rf_links[i][j].set_3d_properties([])

        # Status text
        active_cell = int(np.sum(sinr_cell >= SINR_MIN_CELL_DB))
        active_rf = int(np.sum(sinr_rf >= SINR_MIN_RF_DB) // 2)
        arrived_count = int(sum(d.arrived for d in drones))

        header = "  {:<4}  {:<8}  {:<18}  {:<9}  {:<10}  {:<9}".format(
            "Node", "DistBS", "Cell SINR", "RF Peers", "Thr(Mbps)", "ObsMin"
        )
        rows = [header, "  " + "-" * 78]
        for i in range(N_DRONES):
            d_bs = np.linalg.norm(positions[i] - BS)
            cs = f"{sinr_cell[i]:+5.1f} dB"
            rf_cnt = int(np.sum(sinr_rf[i] >= SINR_MIN_RF_DB))
            obs_s = "INF" if not np.isfinite(nearest_obs_dist[i]) else f"{nearest_obs_dist[i]:.1f}"
            rows.append(
                f"  D{i + 1:<3}  {d_bs:<8.1f}  {cs:<18}  {rf_cnt:<9d}  {thr[i]:<10.2f}  {obs_s:<9}"
            )

        rows.append(
            "\n  Active: {} Cellular | {} RF Links | Arrived: {}/{} | Avg Thr: {:.2f} Mbps".format(
                active_cell,
                active_rf,
                arrived_count,
                N_DRONES,
                float(np.mean(thr)),
            )
        )
        status_text.set_text("\n".join(rows))

        sim_t = frame_idx * DT
        time_text.set_text(f"t = {sim_t:6.1f} / {TOTAL_TIME_S:.0f} s")
        summary_text.set_text(
            "LIVE SUMMARY\n"
            f"Drones:      {N_DRONES}\n"
            f"Obstacles:   {len(obstacles)}\n"
            f"Cell OK:     {active_cell}/{N_DRONES}\n"
            f"RF Links:    {active_rf}\n"
            f"Arrived:     {arrived_count}/{N_DRONES}\n"
            f"Avg Thr:     {np.mean(thr):.2f} Mbps"
        )

        artists = [obs_scatter, status_text, time_text, summary_text]
        artists.extend(trails)
        artists.extend(drone_markers)
        artists.extend(labels)
        artists.extend(cell_links)
        artists.extend(us_lines)
        artists.extend(radar_lines)
        for i in range(N_DRONES):
            artists.extend(lidar_lines[i])
        for i in range(N_DRONES):
            for j in range(i + 1, N_DRONES):
                artists.append(rf_links[i][j])
        return artists

    _ani = animation.FuncAnimation(
        fig,
        update,
        frames=total_frames,
        interval=1000 // FPS,
        blit=False,
        cache_frame_data=False,
        repeat=False,
    )

    plt.show()


if __name__ == "__main__":
    main()
