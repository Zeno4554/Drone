"""
Drone Setup Map component.

Renders an interactive Folium map where the user clicks to place
start (▲) and end (✕) markers for each drone.

Uses st_folium() which returns last_clicked lat/lon back to Python,
so no custom JS component is needed.
"""

from __future__ import annotations

import folium
from streamlit_folium import st_folium

# One colour per drone (tab10-style, matches Plotly + canvas)
DRONE_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"]

_DEFAULT_CENTER = [13.0160, 77.5700]   # Bengaluru
_DEFAULT_ZOOM   = 13


def _drone_color(idx: int) -> str:
    return DRONE_COLORS[idx % len(DRONE_COLORS)]


def render_setup_map(
    drone_configs: list[dict],
    center:        list[float] = _DEFAULT_CENTER,
    zoom:          int         = _DEFAULT_ZOOM,
    height:        int         = 460,
    map_key:       str         = "setup_map",
) -> dict | None:
    """
    Render a Folium map for placing drone start/end markers.

    Parameters
    ----------
    drone_configs : list of dicts, one per drone:
        {
          "id":    "D1",
          "color": "#e74c3c",
          "start": [lat, lon] | None,
          "end":   [lat, lon] | None,
        }
    center : [lat, lon] map center
    zoom   : initial zoom level
    height : component height in pixels
    map_key : unique st_folium key (prevents state collisions between reruns)

    Returns
    -------
    st_folium output dict — check output["last_clicked"] for new clicks.
    """
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="CartoDB dark_matter",
        prefer_canvas=True,
    )

    # Draw existing markers and connecting lines
    for d in drone_configs:
        color = d.get("color", "#ffffff")

        if d.get("start"):
            lat, lon = d["start"]
            folium.CircleMarker(
                [lat, lon],
                radius=7,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                tooltip=f"{d['id']} — Start",
            ).add_to(m)
            folium.Marker(
                [lat, lon],
                icon=folium.DivIcon(
                    html=f'<div style="font-size:10px;font-weight:bold;'
                         f'color:{color};text-shadow:0 0 3px #000;">'
                         f'▲ {d["id"]}</div>',
                    icon_size=(40, 16),
                    icon_anchor=(0, 16),
                ),
            ).add_to(m)

        if d.get("end"):
            lat, lon = d["end"]
            folium.CircleMarker(
                [lat, lon],
                radius=7,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.5,
                dash_array="6",
                tooltip=f"{d['id']} — End",
            ).add_to(m)
            folium.Marker(
                [lat, lon],
                icon=folium.DivIcon(
                    html=f'<div style="font-size:10px;font-weight:bold;'
                         f'color:{color};text-shadow:0 0 3px #000;">'
                         f'✕ {d["id"]}</div>',
                    icon_size=(40, 16),
                    icon_anchor=(0, 16),
                ),
            ).add_to(m)

        # Dotted line start → end
        if d.get("start") and d.get("end"):
            folium.PolyLine(
                [d["start"], d["end"]],
                color=color,
                weight=1.5,
                dash_array="6",
                opacity=0.55,
                tooltip=f"{d['id']} path",
            ).add_to(m)

    return st_folium(
        m,
        width="100%",
        height=height,
        key=map_key,
        returned_objects=["last_clicked"],
    )
