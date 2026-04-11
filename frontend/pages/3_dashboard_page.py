"""Dashboard page - Real-time fleet monitoring."""

import json
import streamlit as st
import pandas as pd
import time
from frontend.services.api_client import APIClient
from frontend.components.map_renderer import (
    create_base_map, add_buildings_to_map, add_delivery_nodes_to_map,
    add_drone_position_to_map, add_orders_to_map, add_route_to_map,
)
from frontend.components.live_map import render_live_map
import streamlit_folium as stf


def show(api_url: str):
    """Display dashboard page."""
    st.title("📊 Operator Dashboard")
    
    api = APIClient(api_url)

    # ---- Dynamic metrics ----
    telemetry = api.get_current_telemetry()
    all_orders = api.get_orders()
    placed = [o for o in all_orders if o["status"] == "placed"]
    assigned = [o for o in all_orders if o["status"] == "assigned"]
    in_transit = [o for o in all_orders if o["status"] == "in-transit"]
    delivered = [o for o in all_orders if o["status"] == "delivered"]

    min_battery = min((d["battery_percent"] for d in telemetry), default=100)
    any_rth = any(d.get("mode") == "RTH" for d in telemetry)
    fleet_health = "RTH active" if any_rth else ("Low battery" if min_battery < 25 else "Good")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Active Drones", len(telemetry))
    with col2:
        st.metric("Pending Orders", len(placed))
    with col3:
        st.metric("In-Transit", len(in_transit))
    with col4:
        st.metric("Fleet Health", fleet_health)
    
    st.divider()

    # ---- Live WebSocket map ----
    st.subheader("🗺️ Live Fleet Positions (WebSocket)")
    render_live_map(api_url, height=450)

    st.divider()

    # ---- Static Folium snapshot with orders / routes ----
    st.subheader("📍 Fleet Snapshot & Active Routes")

    buildings_geojson = api.get_buildings_geojson()
    nodes_geojson = api.get_nodes_geojson()
    orders_geojson = api.get_orders_geojson()

    map_obj = create_base_map()
    add_buildings_to_map(map_obj, buildings_geojson)
    add_delivery_nodes_to_map(map_obj, nodes_geojson)
    add_orders_to_map(map_obj, orders_geojson)

    if telemetry:
        for drone in telemetry:
            add_drone_position_to_map(map_obj, drone, is_active=(drone.get("battery_percent", 0) > 5))

    # Draw routes for in-transit / assigned orders
    for order in assigned + in_transit:
        route_raw = order.get("route_json") if isinstance(order, dict) else None
        if not route_raw:
            detail = api.get_order(order["order_id"])
            route_raw = detail.get("route_json") if detail else None
        if route_raw:
            try:
                wps = json.loads(route_raw) if isinstance(route_raw, str) else route_raw
                add_route_to_map(map_obj, wps)
            except Exception:
                pass

    stf.st_folium(map_obj, width=700, height=500, returned_objects=[])
    
    st.divider()
    
    # ---- Fleet status table ----
    st.subheader("📡 Telemetry Status")
    
    if telemetry:
        telemetry_data = []
        for drone in telemetry:
            telemetry_data.append({
                "Drone": drone["drone_id"],
                "Battery": f"{drone['battery_percent']:.1f}%",
                "Altitude": f"{drone['altitude_msl']:.1f}m",
                "Speed": f"{drone['speed_ms']:.1f} m/s",
                "Mode": drone["mode"],
                "Available": "Yes" if drone.get("available") else "No",
                "Order": drone.get("assigned_order_id") or "—",
            })
        df = pd.DataFrame(telemetry_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No telemetry data available")

    st.divider()

    # ---- Order summary ----
    st.subheader("📦 Order Summary")
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("Total", len(all_orders))
    with col_b:
        st.metric("Assigned", len(assigned))
    with col_c:
        st.metric("Delivered", len(delivered))
    with col_d:
        failed = len([o for o in all_orders if o["status"] == "failed"])
        st.metric("Failed", failed)


# ---- Top-level execution for Streamlit multi-page ----
api_url = st.secrets.get("API_URL", "http://localhost:8000")
show(api_url)
