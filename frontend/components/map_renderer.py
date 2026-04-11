"""Frontend components - Map rendering utilities."""

import json
import folium
from folium import plugins
from typing import List, Dict, Optional
import streamlit as st


def create_base_map(center_lat: float = 13.0, center_lon: float = 77.6, zoom: int = 12) -> folium.Map:
    """Create a base folium map centered on Bengaluru with scroll-wheel zoom."""
    map_obj = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom,
        tiles="OpenStreetMap",
        scrollWheelZoom=True,
    )
    return map_obj


def add_buildings_to_map(map_obj: folium.Map, buildings_geojson: Dict, selected_building_id: str = None):
    """Add buildings as markers to map."""
    if not buildings_geojson or "features" not in buildings_geojson:
        return
    
    for feature in buildings_geojson["features"]:
        props = feature["properties"]
        coords = feature["geometry"]["coordinates"]
        lat, lon = coords[1], coords[0]
        
        color = "blue" if props["building_id"] != selected_building_id else "red"
        
        popup_text = f"""
        <b>{props['name']}</b><br>
        Height: {props['height_m']:.1f}m<br>
        Top: {props['top_elev_msl']:.1f}m MSL<br>
        Building ID: {props['building_id']}
        """
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_text, max_width=250),
            tooltip=props["name"],
            icon=folium.Icon(color=color, icon="info-sign"),
        ).add_to(map_obj)


def add_delivery_nodes_to_map(map_obj: folium.Map, nodes_geojson: Dict, selected_node_id: str = None):
    """Add delivery nodes as markers to map."""
    if not nodes_geojson or "features" not in nodes_geojson:
        return
    
    for feature in nodes_geojson["features"]:
        props = feature["properties"]
        coords = feature["geometry"]["coordinates"]
        lat, lon = coords[1], coords[0]
        
        color = "green" if props["node_id"] != selected_node_id else "orange"
        icon_name = "arrow-down" if props["node_type"] == "rooftop" else "cube"
        
        popup_text = f"""
        <b>{props['node_name']}</b><br>
        Type: {props['node_type']}<br>
        Altitude MSL: {props['altitude_msl']:.1f}m<br>
        Height AGL: {props['height_agl']:.1f}m<br>
        Node ID: {props['node_id']}
        """
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_text, max_width=250),
            tooltip=props["node_name"],
            icon=folium.Icon(color=color, icon=icon_name),
        ).add_to(map_obj)


def add_risk_zones_to_map(map_obj: folium.Map, risk_geojson: Dict):
    """Add risk zones as colored circles to map."""
    if not risk_geojson or "features" not in risk_geojson:
        return
    
    for feature in risk_geojson["features"]:
        props = feature["properties"]
        coords = feature["geometry"]["coordinates"]
        lat, lon = coords[1], coords[0]
        
        color_map = {
            "green": "#00ff00",
            "grey": "#808080",
            "yellow": "#ffff00",
            "red": "#ff0000",
            "black": "#000000",
        }
        
        color = color_map.get(props["zone_color"], "#808080")
        
        popup_text = f"""
        <b>Risk Zone</b><br>
        Risk: {props['risk_score']:.2f}<br>
        Zone: {props['zone_color'].upper()}<br>
        Success Rate: {props['success_rate']*100:.1f}%
        """
        
        folium.Circle(
            location=[lat, lon],
            radius=100,
            popup=folium.Popup(popup_text, max_width=200),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.3,
            weight=2,
        ).add_to(map_obj)


def add_orders_to_map(map_obj: folium.Map, orders_geojson: Dict):
    """Add active orders to map with status-colored markers."""
    if not orders_geojson or "features" not in orders_geojson:
        return

    status_colors = {
        "placed": "lightblue",
        "assigned": "orange",
        "in-transit": "purple",
    }

    for feature in orders_geojson["features"]:
        props = feature["properties"]
        coords = feature["geometry"]["coordinates"]
        lat, lon = coords[1], coords[0]

        color = status_colors.get(props["status"], "gray")

        popup_text = f"""
        <b>Order {props['order_id']}</b><br>
        Status: {props['status']}<br>
        Payload: {props['payload_weight_kg']:.1f} kg<br>
        Drone: {props.get('assigned_drone_id') or 'unassigned'}
        """

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_text, max_width=250),
            tooltip=f"Order {props['order_id'][:16]}",
            icon=folium.Icon(color=color, icon="shopping-cart", prefix="fa"),
        ).add_to(map_obj)

        # Draw route polyline if the order carries route data
        route_raw = props.get("route_json")
        if route_raw:
            try:
                waypoints = json.loads(route_raw) if isinstance(route_raw, str) else route_raw
                _add_ant_path(map_obj, waypoints, color="#7c3aed")
            except Exception:
                pass


def add_route_to_map(map_obj: folium.Map, waypoints: List[Dict], use_ant_path: bool = True):
    """Add planned route as an animated AntPath (or plain polyline) to map."""
    if not waypoints or len(waypoints) < 2:
        return
    
    coords = [(wp["latitude"], wp["longitude"]) for wp in waypoints]

    if use_ant_path:
        _add_ant_path(map_obj, waypoints, color="#7c3aed")
    else:
        folium.PolyLine(
            coords, color="purple", weight=3, opacity=0.8, popup="Planned Route",
        ).add_to(map_obj)
    
    folium.Marker(
        location=coords[0],
        popup="Start",
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(map_obj)
    
    folium.Marker(
        location=coords[-1],
        popup="Destination",
        icon=folium.Icon(color="red", icon="stop"),
    ).add_to(map_obj)
    
    for i, coord in enumerate(coords[1:-1], 1):
        folium.CircleMarker(
            location=coord, radius=5, popup=f"Waypoint {i}",
            color="purple", fill=True, fillColor="purple", fillOpacity=0.7,
        ).add_to(map_obj)


def _add_ant_path(map_obj: folium.Map, waypoints: List[Dict], color: str = "#7c3aed"):
    """Render an animated AntPath polyline for a list of waypoints."""
    coords = [(wp["latitude"], wp["longitude"]) for wp in waypoints]
    if len(coords) < 2:
        return
    plugins.AntPath(
        locations=coords,
        color=color,
        weight=4,
        opacity=0.7,
        dash_array=[10, 20],
        delay=1000,
        popup="Route",
    ).add_to(map_obj)


def add_drone_position_to_map(map_obj: folium.Map, drone_data: Dict, is_active: bool = True):
    """Add drone current position to map."""
    if not drone_data:
        return
    
    color = "green" if is_active else "gray"
    icon_name = "plane" if is_active else "stop"
    
    popup_text = f"""
    <b>{drone_data['drone_id']}</b><br>
    Altitude: {drone_data['altitude_msl']:.1f}m<br>
    Speed: {drone_data['speed_ms']:.1f} m/s<br>
    Battery: {drone_data['battery_percent']:.1f}%<br>
    Mode: {drone_data['mode']}
    """
    
    folium.Marker(
        location=[drone_data["latitude"], drone_data["longitude"]],
        popup=folium.Popup(popup_text, max_width=250),
        tooltip=drone_data["drone_id"],
        icon=folium.Icon(color=color, icon=icon_name, prefix="fa"),
    ).add_to(map_obj)
    
    if drone_data["speed_ms"] > 0.5:
        heading = drone_data["heading_deg"]
        end_lat = drone_data["latitude"] + 0.001 * (heading / 360)
        end_lon = drone_data["longitude"] + 0.001 * ((heading - 90) / 360)
        
        folium.PolyLine(
            [[drone_data["latitude"], drone_data["longitude"]], [end_lat, end_lon]],
            color="green", weight=2, opacity=0.6,
        ).add_to(map_obj)
