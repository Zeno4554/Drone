"""Dashboard page - Real-time fleet monitoring."""

import streamlit as st
import pandas as pd
import time
from services.api_client import APIClient
from components.map_renderer import (
    create_base_map, add_buildings_to_map, add_delivery_nodes_to_map,
    add_drone_position_to_map
)
import streamlit_folium as stf


def show(api_url: str):
    """Display dashboard page."""
    st.title("📊 Operator Dashboard")
    
    api = APIClient(api_url)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Active Drones", "3")
    
    with col2:
        st.metric("Pending Orders", "2")
    
    with col3:
        st.metric("Fleet Health", "✅ Good")
    
    st.divider()
    
    # Auto-refresh toggle
    col_refresh, col_interval = st.columns([1, 2])
    with col_refresh:
        auto_refresh = st.checkbox("🔄 Auto-refresh", value=False)
    with col_interval:
        refresh_interval = st.slider("Refresh interval (s)", 1, 30, 5) if auto_refresh else 5
    
    # Fleet map
    st.subheader("🗺️ Fleet Positions")
    
    # Get telemetry
    telemetry = api.get_current_telemetry()
    
    # Get map data
    buildings_geojson = api.get_buildings_geojson()
    nodes_geojson = api.get_nodes_geojson()
    
    # Create map
    map_obj = create_base_map()
    add_buildings_to_map(map_obj, buildings_geojson)
    add_delivery_nodes_to_map(map_obj, nodes_geojson)
    
    # Add drone positions
    if telemetry:
        for drone in telemetry:
            add_drone_position_to_map(map_obj, drone, is_active=(drone.get("battery_percent", 0) > 5))
    
    # Display map
    stf.folium_static(map_obj, width=700, height=600)
    
    st.divider()
    
    # Fleet status table
    st.subheader("📡 Telemetry Status")
    
    if telemetry:
        telemetry_data = []
        for drone in telemetry:
            telemetry_data.append({
                "Drone ID": drone["drone_id"],
                "Latitude": f"{drone['latitude']:.4f}",
                "Longitude": f"{drone['longitude']:.4f}",
                "Alt MSL": f"{drone['altitude_msl']:.1f}m",
                "Speed": f"{drone['speed_ms']:.1f}m/s",
                "Battery": f"{drone['battery_percent']:.1f}%",
                "Mode": drone["mode"],
                "GPS Sats": drone["gps_satellites"],
            })
        
        df = pd.DataFrame(telemetry_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No telemetry available")
    
    st.divider()
    
    # Emergency controls
    st.subheader("🚨 Emergency Controls")
    
    if telemetry:
        col1, col2, col3 = st.columns(3)
        
        for i, drone in enumerate(telemetry):
            if i == 0:
                col = col1
            elif i == 1:
                col = col2
            else:
                col = col3
            
            with col:
                st.write(f"**{drone['drone_id']}**")
                
                col_a, col_b = st.columns(2)
                
                with col_a:
                    if st.button("🏠 RTH", key=f"rth_{drone['drone_id']}", help="Return to Home"):
                        api.emergency_rth(
                            drone["drone_id"],
                            12.9716,  # Home lat
                            77.5946,  # Home lon
                            950.0     # Home alt
                        )
                        st.success(f"RTH initiated for {drone['drone_id']}")
                
                with col_b:
                    if st.button("⬇️  Land", key=f"land_{drone['drone_id']}", help="Land drone"):
                        api.land_drone(drone["drone_id"])
                        st.success(f"Landing initiated for {drone['drone_id']}")
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()


# ---- Top-level execution for Streamlit multi-page ----
api_url = st.secrets.get("API_URL", "http://localhost:8000")
show(api_url)
