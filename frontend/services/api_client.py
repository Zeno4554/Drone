"""Frontend services - API client for Streamlit."""

import requests
from typing import List, Dict, Optional
import streamlit as st

class APIClient:
    """Client for FastAPI backend."""
    
    def __init__(self, base_url: str):
        """Initialize API client."""
        self.base_url = base_url.rstrip("/")
        self.api_v1 = f"{self.base_url}/api/v1"
        self.session = requests.Session()
    
    # Buildings
    def get_buildings(self) -> List[Dict]:
        """Get all buildings."""
        try:
            resp = self.session.get(f"{self.api_v1}/buildings")
            return resp.json() if resp.status_code == 200 else []
        except Exception as e:
            st.error(f"Failed to get buildings: {e}")
            return []
    
    def get_building(self, building_id: str) -> Optional[Dict]:
        """Get single building."""
        try:
            resp = self.session.get(f"{self.api_v1}/buildings/{building_id}")
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None
    
    # Delivery Nodes
    def get_delivery_nodes(self, building_id: str = None) -> List[Dict]:
        """Get delivery nodes (optionally filtered by building)."""
        try:
            if building_id:
                resp = self.session.get(f"{self.api_v1}/nodes/building/{building_id}")
            else:
                resp = self.session.get(f"{self.api_v1}/nodes")
            return resp.json() if resp.status_code == 200 else []
        except Exception as e:
            st.error(f"Failed to get delivery nodes: {e}")
            return []
    
    def get_delivery_node(self, node_id: str) -> Optional[Dict]:
        """Get single delivery node."""
        try:
            resp = self.session.get(f"{self.api_v1}/nodes/{node_id}")
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None
    
    # Orders
    def get_orders(self, status: str = None) -> List[Dict]:
        """Get all orders."""
        try:
            params = {"status": status} if status else {}
            resp = self.session.get(f"{self.api_v1}/orders", params=params)
            return resp.json() if resp.status_code == 200 else []
        except Exception as e:
            st.error(f"Failed to get orders: {e}")
            return []
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get single order."""
        try:
            resp = self.session.get(f"{self.api_v1}/orders/{order_id}")
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None
    
    def place_order(self, destination_node_id: str, payload_weight_kg: float, description: str = None) -> Optional[Dict]:
        """Place a new order."""
        try:
            data = {
                "destination_node_id": destination_node_id,
                "payload_weight_kg": payload_weight_kg,
                "payload_description": description,
            }
            resp = self.session.post(f"{self.api_v1}/orders", json=data)
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            st.error(f"Failed to place order: {e}")
            return None
    
    def update_order(self, order_id: str, status: str = None, drone_id: str = None) -> Optional[Dict]:
        """Update order."""
        try:
            data = {}
            if status:
                data["status"] = status
            if drone_id:
                data["assigned_drone_id"] = drone_id
            resp = self.session.patch(f"{self.api_v1}/orders/{order_id}", json=data)
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            st.error(f"Failed to update order: {e}")
            return None
    
    # Routes
    def plan_route(self, source_lat: float, source_lon: float, source_alt: float, dest_node_id: str) -> Optional[Dict]:
        """Plan a route."""
        try:
            data = {
                "source_lat": source_lat,
                "source_lon": source_lon,
                "source_alt_msl": source_alt,
                "destination_node_id": dest_node_id,
            }
            resp = self.session.post(f"{self.api_v1}/routes", json=data)
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            st.error(f"Failed to plan route: {e}")
            return None
    
    def validate_route(self, waypoints: List[Dict]) -> Optional[Dict]:
        """Validate a route."""
        try:
            resp = self.session.post(f"{self.api_v1}/routes/validate", json=waypoints)
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None
    
    # Map Data
    def get_buildings_geojson(self) -> Optional[Dict]:
        """Get buildings as GeoJSON."""
        try:
            resp = self.session.get(f"{self.api_v1}/map/buildings/geojson")
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None
    
    def get_nodes_geojson(self) -> Optional[Dict]:
        """Get delivery nodes as GeoJSON."""
        try:
            resp = self.session.get(f"{self.api_v1}/map/nodes/geojson")
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None
    
    def get_risk_zones_geojson(self, min_risk: float = 0.0) -> Optional[Dict]:
        """Get risk zones as GeoJSON."""
        try:
            params = {"min_risk": min_risk}
            resp = self.session.get(f"{self.api_v1}/map/risk-zones/geojson", params=params)
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None
    
    def get_map_bounds(self) -> Optional[Dict]:
        """Get recommended map bounds."""
        try:
            resp = self.session.get(f"{self.api_v1}/map/bounds")
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None
    
    # Telemetry
    def get_current_telemetry(self) -> List[Dict]:
        """Get current telemetry for all drones."""
        try:
            resp = self.session.get(f"{self.api_v1}/telemetry/current")
            return resp.json() if resp.status_code == 200 else []
        except Exception:
            return []
    
    def get_drone_telemetry(self, drone_id: str) -> Optional[Dict]:
        """Get telemetry for specific drone."""
        try:
            resp = self.session.get(f"{self.api_v1}/telemetry/drone/{drone_id}")
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None
    
    def emergency_rth(self, drone_id: str, home_lat: float, home_lon: float, home_alt: float) -> bool:
        """Trigger emergency RTH."""
        try:
            data = {
                "home_lat": home_lat,
                "home_lon": home_lon,
                "home_alt_msl": home_alt,
            }
            resp = self.session.post(f"{self.api_v1}/telemetry/drone/{drone_id}/emergency-rth", json=data)
            return resp.status_code == 200
        except Exception:
            return False
    
    def land_drone(self, drone_id: str) -> bool:
        """Command drone to land."""
        try:
            resp = self.session.post(f"{self.api_v1}/telemetry/drone/{drone_id}/land")
            return resp.status_code == 200
        except Exception:
            return False
    
    # Drone assignment
    def assign_drone(self, order_id: str) -> Optional[Dict]:
        """Auto-assign best available drone to an order."""
        try:
            resp = self.session.post(f"{self.api_v1}/orders/{order_id}/assign-drone")
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            st.error(f"Failed to assign drone: {e}")
            return None

    def assign_route_to_order(self, order_id: str, waypoints: list, distance_m: float, duration_s: float) -> Optional[Dict]:
        """Attach a planned route to an order."""
        try:
            resp = self.session.post(
                f"{self.api_v1}/orders/{order_id}/assign-route",
                json=waypoints,
                params={"distance_m": distance_m, "duration_s": duration_s},
            )
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            st.error(f"Failed to assign route: {e}")
            return None

    def release_drone(self, order_id: str) -> bool:
        """Release a drone from a completed/cancelled order."""
        try:
            resp = self.session.post(f"{self.api_v1}/orders/{order_id}/release-drone")
            return resp.status_code == 200
        except Exception:
            return False

    # Map GeoJSON helpers
    def get_orders_geojson(self, status: str = None) -> Optional[Dict]:
        """Get active orders as GeoJSON."""
        try:
            params = {"status": status} if status else {}
            resp = self.session.get(f"{self.api_v1}/map/orders/geojson", params=params)
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None

    # Bootstrap / setup
    def bootstrap(self) -> Optional[Dict]:
        """Trigger demo data bootstrap on the backend."""
        try:
            resp = self.session.post(f"{self.api_v1}/setup/bootstrap")
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None

    def get_setup_status(self) -> Optional[Dict]:
        """Get DB row counts."""
        try:
            resp = self.session.get(f"{self.api_v1}/setup/status")
            return resp.json() if resp.status_code == 200 else None
        except Exception:
            return None

    @property
    def telemetry_ws_url(self) -> str:
        """WebSocket URL for the telemetry stream."""
        ws = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{ws}/api/v1/telemetry/ws"
