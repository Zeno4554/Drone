"""Map page - Building and delivery node selection with 3D map."""

import json
import streamlit as st
import pandas as pd
from frontend.services.api_client import APIClient
from frontend.components.map_renderer import (
    create_base_map, add_buildings_to_map, add_delivery_nodes_to_map,
    add_risk_zones_to_map, add_route_to_map, add_orders_to_map,
)
import streamlit_folium as stf


def show(api_url: str):
    """Display map page."""
    st.title("🗺️ Delivery Locations")
    
    api = APIClient(api_url)
    
    col1, col2 = st.columns([1, 3])
    
    # Left sidebar - selectors
    with col1:
        st.subheader("Selection")
        
        buildings = api.get_buildings()
        if not buildings:
            st.error("Failed to load buildings. Is the backend running?")
            return
        
        building_options = {b["name"]: b for b in buildings}
        selected_building_name = st.selectbox(
            "🏢 Select Building",
            list(building_options.keys())
        )
        selected_building = building_options[selected_building_name]
        
        nodes = api.get_delivery_nodes(selected_building["building_id"])
        
        selected_node = None
        if nodes:
            node_options = {n["node_name"]: n for n in nodes}
            selected_node_name = st.selectbox(
                "📍 Select Delivery Node",
                list(node_options.keys())
            )
            selected_node = node_options[selected_node_name]
            
            st.divider()
            st.write("**Node Details**")
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Type", selected_node["node_type"])
                st.metric("Height AGL", f"{selected_node['height_agl']:.1f}m")
            with col_b:
                st.metric("Altitude MSL", f"{selected_node['altitude_msl']:.1f}m")
                st.metric("Max Payload", f"{selected_node['max_payload_kg']:.1f}kg")
            
            st.divider()
            
            if st.button("📍 Plan Route from Here", key="plan_route_btn"):
                route = api.plan_route(12.9716, 77.5946, 980.0, selected_node["node_id"])
                if route and "waypoints" in route:
                    st.session_state.last_route_waypoints = route["waypoints"]
                    st.info(
                        f"Route planned — {route['total_distance_m']:.0f} m, "
                        f"~{route['estimated_duration_s']:.0f} s, "
                        f"risk {route['risk_score']:.2f}"
                    )
                else:
                    st.error("Route planning failed")
        else:
            st.warning("No delivery nodes for this building")
    
    # Right side - map
    with col2:
        st.subheader("Map View")
        
        buildings_geojson = api.get_buildings_geojson()
        nodes_geojson = api.get_nodes_geojson()
        risk_geojson = api.get_risk_zones_geojson(min_risk=0.3)
        orders_geojson = api.get_orders_geojson()
        
        map_obj = create_base_map()
        
        add_buildings_to_map(map_obj, buildings_geojson, selected_building["building_id"])
        if selected_node:
            add_delivery_nodes_to_map(map_obj, nodes_geojson, selected_node["node_id"])
        else:
            add_delivery_nodes_to_map(map_obj, nodes_geojson)
        add_risk_zones_to_map(map_obj, risk_geojson)
        add_orders_to_map(map_obj, orders_geojson)

        # Draw the last planned route (or route from a tracked order)
        if "last_route_waypoints" in st.session_state:
            add_route_to_map(map_obj, st.session_state.last_route_waypoints)
        
        stf.st_folium(map_obj, width=700, height=600, returned_objects=[])
    
    # Bottom - Building/Node info table
    st.divider()
    st.subheader("📊 All Delivery Nodes")
    
    nodes_data = []
    for building in buildings:
        building_nodes = api.get_delivery_nodes(building["building_id"])
        for node in building_nodes:
            nodes_data.append({
                "Building": building["name"],
                "Node": node["node_name"],
                "Type": node["node_type"],
                "Altitude MSL": f"{node['altitude_msl']:.1f}m",
                "Height AGL": f"{node['height_agl']:.1f}m",
                "Marker ID": node["marker_id"] or "—",
            })
    
    if nodes_data:
        df = pd.DataFrame(nodes_data)
        st.dataframe(df, use_container_width=True)


# ---- Top-level execution for Streamlit multi-page ----
api_url = st.secrets.get("API_URL", "http://localhost:8000")
show(api_url)
