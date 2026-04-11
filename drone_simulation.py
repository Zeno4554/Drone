"""
Drone Sensor Simulation — 3D
==============================
3D simulation of a drone moving randomly inside a 10×10×10 room.
Obstacles spawn and despawn randomly during the simulation.

Configure sensors in ACTIVE_SENSORS below.
Set any sensor to False to disable it — any combination is valid.
"""

import math
import random

import matplotlib.animation as animation
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

# ─────────────────────────────────────────────────────────────────────────────
#  USER CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

ROOM_SIZE = 10          # Room is ROOM_SIZE × ROOM_SIZE × ROOM_SIZE units
FPS       = 20          # Animation frames per second
MAX_STEP  = 0.25        # Max drone movement per frame

# ── Sensor toggle ─────────────────────────────────────────────────────────────
# Set True / False to enable or disable each sensor independently.
ACTIVE_SENSORS = {
    "ultrasonic": True,   # Single forward-facing beam  (short range, yellow)
    "lidar":      True,   # Horizontal 360° fan of rays (medium range, green)
    "radar":      True,   # Faint range circle          (long range, blue)
}

# ── Sensor parameters ─────────────────────────────────────────────────────────
ULTRASONIC_RANGE = 3.0   # Max range in units
LIDAR_RAYS       = 36    # Number of evenly-spaced horizontal LiDAR beams
LIDAR_RANGE      = 4.5   # Max LiDAR range in units
RADAR_RANGE      = 6.5   # Radius of radar circle in units
NOISE_STD        = 0.08  # Gaussian noise std-dev on all ray distances

# ── Dynamic obstacle settings ─────────────────────────────────────────────────
INITIAL_OBSTACLES   = 4     # Obstacles present at start
MAX_OBSTACLES       = 14    # Hard cap
SPAWN_PROBABILITY   = 0.05  # Chance per frame to add a new obstacle
DESPAWN_PROBABILITY = 0.02  # Chance per frame to remove the oldest obstacle
OBSTACLE_RADIUS     = 0.35  # Collision detection radius (ray marching)

# ─────────────────────────────────────────────────────────────────────────────
#  OBSTACLE STATE  (mutable list — updated every frame)
# ─────────────────────────────────────────────────────────────────────────────

obstacles: list[tuple[float, float, float]] = [
    (
        random.uniform(1.0, ROOM_SIZE - 1.0),
        random.uniform(1.0, ROOM_SIZE - 1.0),
        random.uniform(1.0, ROOM_SIZE - 1.0),
    )
    for _ in range(INITIAL_OBSTACLES)
]


def maybe_spawn_obstacle() -> None:
    """Randomly add a new obstacle if below the cap."""
    if random.random() < SPAWN_PROBABILITY and len(obstacles) < MAX_OBSTACLES:
        obstacles.append((
            random.uniform(1.0, ROOM_SIZE - 1.0),
            random.uniform(1.0, ROOM_SIZE - 1.0),
            random.uniform(1.0, ROOM_SIZE - 1.0),
        ))


def maybe_despawn_obstacle() -> None:
    """Randomly remove the oldest obstacle, keeping at least INITIAL_OBSTACLES."""
    if random.random() < DESPAWN_PROBABILITY and len(obstacles) > INITIAL_OBSTACLES:
        obstacles.pop(0)


# ─────────────────────────────────────────────────────────────────────────────
#  DRONE
# ─────────────────────────────────────────────────────────────────────────────

class Drone:
    """Drone that wanders in 3D space and bounces off all six room walls."""

    def __init__(self, x: float, y: float, z: float) -> None:
        self.x  = x
        self.y  = y
        self.z  = z
        self.az = random.uniform(0, 2 * math.pi)   # azimuth heading (radians)
        self.el = 0.0                               # elevation heading (radians)

    def move(self) -> None:
        # Drift heading organically
        self.az += random.uniform(-0.4, 0.4)
        self.el += random.uniform(-0.12, 0.12)
        self.el  = max(-0.45, min(0.45, self.el))  # limit pitch

        speed = random.uniform(0.05, MAX_STEP)
        dx = math.cos(self.az) * math.cos(self.el) * speed
        dy = math.sin(self.az) * math.cos(self.el) * speed
        dz = math.sin(self.el) * speed

        m = 0.1
        nx = self.x + dx
        ny = self.y + dy
        nz = self.z + dz

        # Bounce: reflect heading component that caused the wall hit
        if nx < m or nx > ROOM_SIZE - m:
            self.az = math.pi - self.az
            nx = max(m, min(ROOM_SIZE - m, nx))
        if ny < m or ny > ROOM_SIZE - m:
            self.az = -self.az
            ny = max(m, min(ROOM_SIZE - m, ny))
        if nz < m or nz > ROOM_SIZE - m:
            self.el = -self.el
            nz = max(m, min(ROOM_SIZE - m, nz))

        self.x, self.y, self.z = nx, ny, nz

    @property
    def forward(self) -> tuple[float, float, float]:
        """Unit vector in the drone's current facing direction."""
        return (
            math.cos(self.az) * math.cos(self.el),
            math.sin(self.az) * math.cos(self.el),
            math.sin(self.el),
        )


# ─────────────────────────────────────────────────────────────────────────────
#  SENSOR HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def cast_ray(
    ox: float, oy: float, oz: float,
    dx: float, dy: float, dz: float,
    max_range: float,
) -> float:
    """
    March a ray from (ox, oy, oz) in normalised direction (dx, dy, dz).
    Returns the distance to the first obstacle or wall, with Gaussian noise.
    """
    step = 0.05
    dist = 0.0

    while dist < max_range:
        dist += step
        rx = ox + dx * dist
        ry = oy + dy * dist
        rz = oz + dz * dist

        # Hit a wall — step back to last valid position inside the room
        if not (0.0 <= rx <= ROOM_SIZE and 0.0 <= ry <= ROOM_SIZE and 0.0 <= rz <= ROOM_SIZE):
            dist = max(0.0, dist - step)
            break

        # Hit an obstacle
        if any(
            math.hypot(rx - ex, ry - ey, rz - ez) < OBSTACLE_RADIUS
            for ex, ey, ez in obstacles
        ):
            dist = max(0.0, dist - step)
            break

    return max(0.0, dist + random.gauss(0, NOISE_STD))


def circle_3d(cx: float, cy: float, cz: float, r: float, n: int = 72):
    """Return (xs, ys, zs) for a horizontal closed circle centred at (cx, cy, cz)."""
    angles = [2 * math.pi * i / n for i in range(n + 1)]
    return (
        [cx + r * math.cos(a) for a in angles],
        [cy + r * math.sin(a) for a in angles],
        [cz] * (n + 1),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  SCENE SETUP
# ─────────────────────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(9, 8))
ax  = fig.add_subplot(111, projection="3d")
fig.patch.set_facecolor("#0d0d1a")

# 3D pane styling
for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
    pane.fill = False
    pane.set_edgecolor("#1a2244")

ax.set_xlim(0, ROOM_SIZE)
ax.set_ylim(0, ROOM_SIZE)
ax.set_zlim(0, ROOM_SIZE)
ax.set_xlabel("X", color="#8888aa", labelpad=6)
ax.set_ylabel("Y", color="#8888aa", labelpad=6)
ax.set_zlabel("Z", color="#8888aa", labelpad=6)
ax.tick_params(colors="#44446a", labelsize=7)
ax.set_title("Drone Sensor Simulation  (3D)", color="#aaaacc", pad=14)
ax.view_init(elev=25, azim=-55)   # comfortable starting view angle

# ── Room wireframe ────────────────────────────────────────────────────────────
S = ROOM_SIZE
_room_edges = [
    # Bottom face
    ([0,S],[0,0],[0,0]), ([0,S],[S,S],[0,0]),
    ([0,0],[0,S],[0,0]), ([S,S],[0,S],[0,0]),
    # Top face
    ([0,S],[0,0],[S,S]), ([0,S],[S,S],[S,S]),
    ([0,0],[0,S],[S,S]), ([S,S],[0,S],[S,S]),
    # Vertical pillars
    ([0,0],[0,0],[0,S]), ([S,S],[0,0],[0,S]),
    ([0,0],[S,S],[0,S]), ([S,S],[S,S],[0,S]),
]
for xs, ys, zs in _room_edges:
    ax.plot(xs, ys, zs, color="#223366", lw=0.9, alpha=0.55)

# ── Obstacles (scatter — updated dynamically each frame) ─────────────────────
obs_scatter = ax.scatter(
    [o[0] for o in obstacles],
    [o[1] for o in obstacles],
    [o[2] for o in obstacles],
    c="#ff4444", s=80, marker="s", depthshade=True, zorder=6,
)

# ── Drone ─────────────────────────────────────────────────────────────────────
drone = Drone(5.0, 5.0, 5.0)
drone_scatter = ax.scatter([5.0], [5.0], [5.0], c="#00ffe0", s=120, depthshade=False, zorder=10)

# ── Sensor artists (pre-created; visibility toggled in update) ────────────────

# Ultrasonic — single yellow forward beam
us_line, = ax.plot([], [], [], "-", color="#ffdd00", lw=2.2, alpha=0.90, zorder=7)

# LiDAR — horizontal fan of green rays
lidar_lines = [
    ax.plot([], [], [], "-", color="#33ff77", lw=0.8, alpha=0.60, zorder=7)[0]
    for _ in range(LIDAR_RAYS)
]

# Radar — faint blue horizontal circle (line-based for easy update)
radar_line, = ax.plot([], [], [], "-", color="#4488ff", lw=1.3, alpha=0.22, zorder=5)

# ── Legend ────────────────────────────────────────────────────────────────────
legend_handles = [
    mpatches.Patch(color="#00ffe0", label="Drone"),
    mpatches.Patch(color="#ff4444", label="Obstacle (dynamic)"),
]
if ACTIVE_SENSORS["ultrasonic"]:
    legend_handles.append(mpatches.Patch(color="#ffdd00", label="Ultrasonic"))
if ACTIVE_SENSORS["lidar"]:
    legend_handles.append(mpatches.Patch(color="#33ff77", label="LiDAR"))
if ACTIVE_SENSORS["radar"]:
    legend_handles.append(mpatches.Patch(color="#4488ff", label="Radar"))

ax.legend(
    handles=legend_handles,
    loc="upper left",
    facecolor="#111122",
    edgecolor="#334466",
    labelcolor="#cccccc",
    fontsize=9,
)

# ─────────────────────────────────────────────────────────────────────────────
#  ANIMATION UPDATE
# ─────────────────────────────────────────────────────────────────────────────

def update(_frame) -> list:
    # ── Move drone ─────────────────────────────────────────────────────────
    drone.move()
    x, y, z = drone.x, drone.y, drone.z

    # ── Manage dynamic obstacles ────────────────────────────────────────────
    maybe_spawn_obstacle()
    maybe_despawn_obstacle()

    # Refresh obstacle scatter with current list
    obs_scatter._offsets3d = (
        [o[0] for o in obstacles],
        [o[1] for o in obstacles],
        [o[2] for o in obstacles],
    )

    # Refresh drone position
    drone_scatter._offsets3d = ([x], [y], [z])

    # ── Ultrasonic ─────────────────────────────────────────────────────────
    if ACTIVE_SENSORS["ultrasonic"]:
        fdx, fdy, fdz = drone.forward
        d = cast_ray(x, y, z, fdx, fdy, fdz, ULTRASONIC_RANGE)
        us_line.set_data_3d(
            [x, x + fdx * d],
            [y, y + fdy * d],
            [z, z + fdz * d],
        )
        us_line.set_visible(True)
    else:
        us_line.set_visible(False)

    # ── LiDAR — rays sweep in the horizontal plane at the drone's z ────────
    for i, line in enumerate(lidar_lines):
        if ACTIVE_SENSORS["lidar"]:
            angle = 2 * math.pi * i / LIDAR_RAYS
            rdx, rdy, rdz = math.cos(angle), math.sin(angle), 0.0
            d = cast_ray(x, y, z, rdx, rdy, rdz, LIDAR_RANGE)
            line.set_data_3d(
                [x, x + rdx * d],
                [y, y + rdy * d],
                [z, z + rdz * d],
            )
            line.set_visible(True)
        else:
            line.set_visible(False)

    # ── Radar — horizontal circle at drone altitude ─────────────────────────
    if ACTIVE_SENSORS["radar"]:
        rx, ry, rz = circle_3d(x, y, z, RADAR_RANGE)
        radar_line.set_data_3d(rx, ry, rz)
        radar_line.set_visible(True)
    else:
        radar_line.set_visible(False)

    return [drone_scatter, obs_scatter, us_line, *lidar_lines, radar_line]


# ─────────────────────────────────────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────────────────────────────────────

ani = animation.FuncAnimation(
    fig, update,
    interval=1000 // FPS,
    blit=False,          # blit=True not supported on 3D axes
    cache_frame_data=False,
)

plt.tight_layout()
plt.show()
