"""
Swarm Mission Page.

Two-phase interactive page:

  SETUP phase
  -----------
  • Sidebar: number of drones, speed, sensor toggles, obstacle settings,
    simulation duration, FPS.
  • Map: click to place each drone's start (▲) then end (✕) point in turn.
  • "Launch Mission" button appears once all start + end points are set.

  RUNNING phase
  -------------
  • Left column  (≈55 %): Leaflet live map — WebSocket 20 fps, real map tiles.
  • Right column (≈45 %): Three.js 3D environment — WebSocket 60 fps, WebGL.
  • Both views drive their own WebSocket connections independently.
  • Sidebar controls: Reset / Stop.
"""

from __future__ import annotations

import streamlit as st
from services.api_client import APIClient
from components.drone_setup_map import (
    DRONE_COLORS,
    render_setup_map,
)
from components.swarm_live_map import render_swarm_live_map
from components.swarm_3d_view import render_swarm_3d_view

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Swarm Mission — AeroCorridor",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ─────────────────────────────────────────────────────────────────
_DEFAULT_CENTER = [13.0160, 77.5700]   # Bengaluru
_DEFAULT_ALT_M  = 80.0
_API_URL        = "http://localhost:8000"


def _api() -> APIClient:
    return APIClient(_API_URL)


def _init_state(n_drones: int) -> None:
    """Initialise (or reset) all session state for the given drone count."""
    st.session_state.n_drones      = n_drones
    st.session_state.phase         = "setup"   # "setup" | "running" | "done"
    st.session_state.session_id    = None
    st.session_state.ref_lat       = None
    st.session_state.ref_lon       = None
    st.session_state.geo_mode      = False
    st.session_state.ws_url        = None
    st.session_state.click_target  = 0         # next slot to fill (0 .. 2n-1)
    st.session_state.drone_configs = [
        {
            "id":    f"D{i + 1}",
            "color": DRONE_COLORS[i % len(DRONE_COLORS)],
            "start": None,
            "end":   None,
        }
        for i in range(n_drones)
    ]


def _all_set(n: int) -> bool:
    configs = st.session_state.get("drone_configs", [])
    return (
        len(configs) == n
        and all(d.get("start") and d.get("end") for d in configs)
    )


def _click_label() -> str:
    idx   = st.session_state.click_target
    n     = st.session_state.n_drones
    if idx >= 2 * n:
        return "All points set — launch when ready"
    drone  = idx // 2
    marker = "Start ▲" if idx % 2 == 0 else "End ✕"
    return f"Click map to place D{drone + 1} {marker}"


# ── State bootstrap ───────────────────────────────────────────────────────────
if "phase" not in st.session_state:
    _init_state(n_drones=3)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🛸 Swarm Mission")
    st.divider()

    n_drones = st.number_input(
        "Number of drones",
        min_value=1, max_value=6,
        value=st.session_state.n_drones,
        step=1,
        disabled=(st.session_state.phase != "setup"),
    )
    if n_drones != st.session_state.n_drones and st.session_state.phase == "setup":
        _init_state(int(n_drones))
        st.rerun()

    st.subheader("Speed (m/s)")
    speed_all = st.slider("All drones", 5, 30, 15,
                          disabled=(st.session_state.phase != "setup"))

    st.subheader("Sensors")
    use_us    = st.checkbox("Ultrasonic", value=True,
                            disabled=(st.session_state.phase != "setup"))
    use_lidar = st.checkbox("LiDAR",      value=True,
                            disabled=(st.session_state.phase != "setup"))
    use_radar = st.checkbox("Radar",      value=True,
                            disabled=(st.session_state.phase != "setup"))

    st.subheader("Obstacles")
    obs_count = st.slider("Count",         0, 20,  8,
                          disabled=(st.session_state.phase != "setup"))
    obs_r_min = st.slider("Min radius (m)", 2, 20,  5,
                          disabled=(st.session_state.phase != "setup"))
    obs_r_max = st.slider("Max radius (m)",10, 60, 30,
                          disabled=(st.session_state.phase != "setup"))

    st.subheader("Simulation")
    total_s = st.slider("Duration (s)", 30, 300, 120, step=10,
                        disabled=(st.session_state.phase != "setup"))
    fps     = st.select_slider("FPS", options=[5, 10, 20], value=20,
                               disabled=(st.session_state.phase != "setup"))

    st.divider()

    # ── Control buttons ───────────────────────────────────────────────────────
    if st.session_state.phase == "setup":
        can_launch = _all_set(int(n_drones))
        if st.button("🚀 Launch Mission", disabled=not can_launch,
                     use_container_width=True):
            configs  = st.session_state.drone_configs
            starts   = [[c["start"][0], c["start"][1], _DEFAULT_ALT_M] for c in configs]
            ends     = [[c["end"][0],   c["end"][1],   _DEFAULT_ALT_M] for c in configs]
            speeds   = [float(speed_all)] * int(n_drones)
            ref_lat  = sum(s[0] for s in starts) / len(starts)
            ref_lon  = sum(s[1] for s in starts) / len(starts)

            result = _api().start_swarm_mission(
                n_drones       = int(n_drones),
                start_points   = starts,
                end_points     = ends,
                speeds         = speeds,
                active_sensors = {
                    "ultrasonic": use_us,
                    "lidar":      use_lidar,
                    "radar":      use_radar,
                },
                total_time_s   = float(total_s),
                fps            = int(fps),
                obs_count      = int(obs_count),
                obs_radius_min = float(obs_r_min),
                obs_radius_max = float(obs_r_max),
                ref_lat        = ref_lat,
                ref_lon        = ref_lon,
            )
            if result:
                st.session_state.session_id = result["session_id"]
                st.session_state.ref_lat    = ref_lat
                st.session_state.ref_lon    = ref_lon
                st.session_state.geo_mode   = result.get("geo_mode", True)
                st.session_state.ws_url     = _api().swarm_mission_ws_url(
                    result["session_id"]
                )
                st.session_state.phase = "running"
                st.rerun()
            else:
                st.error("Failed to start mission — is the backend running?")

    elif st.session_state.phase in ("running", "done"):
        if st.button("🔄 Reset", use_container_width=True):
            sid = st.session_state.session_id
            if sid:
                _api().reset_swarm_mission(sid)
            st.session_state.phase = "running"
            st.rerun()

        if st.button("⏹ Stop & New Mission", use_container_width=True):
            sid = st.session_state.session_id
            if sid:
                _api().delete_swarm_mission(sid)
            _init_state(int(n_drones))
            st.rerun()

    st.divider()
    st.caption("AeroCorridor · Swarm Mission")

# ═══════════════════════════════════════════════════════════════════════════════
# SETUP PHASE
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.phase == "setup":
    st.header("Swarm Mission Setup")
    st.info(_click_label(), icon="📍")

    map_output = render_setup_map(
        drone_configs = st.session_state.drone_configs,
        center        = _DEFAULT_CENTER,
        map_key       = "swarm_setup_map",
    )

    clicked = (map_output or {}).get("last_clicked")
    idx     = st.session_state.click_target
    n       = st.session_state.n_drones

    if clicked and idx < 2 * n:
        drone = idx // 2
        if idx % 2 == 0:
            st.session_state.drone_configs[drone]["start"] = [
                clicked["lat"], clicked["lng"]
            ]
        else:
            st.session_state.drone_configs[drone]["end"] = [
                clicked["lat"], clicked["lng"]
            ]
        st.session_state.click_target += 1
        st.rerun()

    # Configuration table
    st.subheader("Drone configuration")
    rows = []
    for d in st.session_state.drone_configs:
        rows.append({
            "Drone": d["id"],
            "Start": (f"{d['start'][0]:.5f}, {d['start'][1]:.5f}"
                      if d["start"] else "—"),
            "End":   (f"{d['end'][0]:.5f}, {d['end'][1]:.5f}"
                      if d["end"] else "—"),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    if st.session_state.click_target > 0:
        if st.button("↩ Undo last point"):
            st.session_state.click_target -= 1
            idx2  = st.session_state.click_target
            d2    = idx2 // 2
            if idx2 % 2 == 0:
                st.session_state.drone_configs[d2]["start"] = None
            else:
                st.session_state.drone_configs[d2]["end"] = None
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# RUNNING / DONE PHASE
# ═══════════════════════════════════════════════════════════════════════════════
else:
    phase   = st.session_state.phase
    n       = st.session_state.n_drones
    configs = st.session_state.drone_configs

    if phase == "done":
        st.success("Simulation complete. Use Reset or Stop in the sidebar.")

    # ── Live views ────────────────────────────────────────────────────────────
    col_map, col_3d = st.columns([11, 9])

    with col_map:
        st.subheader("Live Map")
        start_pts = [c["start"] for c in configs if c.get("start")]
        end_pts   = [c["end"]   for c in configs if c.get("end")]
        render_swarm_live_map(
            ws_url       = st.session_state.ws_url,
            drone_colors = [c["color"] for c in configs],
            ref_lat      = st.session_state.ref_lat,
            ref_lon      = st.session_state.ref_lon,
            n_drones     = n,
            start_pts    = start_pts,
            end_pts      = end_pts,
            geo_mode     = st.session_state.geo_mode,
            height       = 540,
        )

    with col_3d:
        st.subheader("3D Environment")
        render_swarm_3d_view(
            ws_url       = st.session_state.ws_url,
            drone_colors = [c["color"] for c in configs],
            n_drones     = n,
            height       = 540,
        )

    st.caption(
        "Both views share the same WebSocket stream. "
        "Drag to orbit · Scroll to zoom · Right-drag to pan the 3D view."
    )
