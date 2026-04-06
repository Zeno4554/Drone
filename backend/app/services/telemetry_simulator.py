"""Telemetry simulation for drone tracking."""

import random
import math
from datetime import datetime, timedelta
from typing import Dict, List
from ..config import settings


class TelemetrySimulator:
    """Simulates realistic drone telemetry data."""
    
    def __init__(self, num_drones: int = 3):
        """Initialize telemetry simulator.
        
        Args:
            num_drones: Number of drones to simulate
        """
        self.num_drones = num_drones
        self.drone_states = {}
        self._initialize_drones()
    
    def _initialize_drones(self):
        """Initialize drone states."""
        # Test locations in Bengaluru
        test_locations = [
            {"lat": 12.9716, "lon": 77.5946, "name": "Phoenix Mall"},  # Bangalore central
            {"lat": 12.9716, "lon": 77.6412, "name": "Whitefield"},     # Tech park area
            {"lat": 12.9711, "lon": 77.5532, "name": "Jayanagar"},      # South Bangalore
        ]
        
        for i in range(self.num_drones):
            loc = test_locations[i % len(test_locations)]
            self.drone_states[f"DRONE_{i:03d}"] = {
                "drone_id": f"DRONE_{i:03d}",
                "latitude": loc["lat"],
                "longitude": loc["lon"],
                "altitude_msl": 950.0 + random.uniform(-10, 30),  # 920 + 30-60m AGL
                "velocity_x_ms": random.uniform(-5, 5),  # m/s East
                "velocity_y_ms": random.uniform(-5, 5),  # m/s North
                "velocity_z_ms": random.uniform(-1, 1),  # m/s Up
                "heading_deg": random.uniform(0, 360),
                "pitch_deg": random.uniform(-15, 15),
                "roll_deg": random.uniform(-15, 15),
                "yaw_deg": random.uniform(0, 360),
                "battery_percent": random.uniform(70, 100),
                "armed": "true" if i == 0 else "false",
                "mode": "AUTO" if i == 0 else "STABILIZE",
                "gps_satellites": random.randint(15, 20),
                "signal_strength_db": random.uniform(-80, -60),
                "flight_id": f"FL_{i:03d}" if i == 0 else None,
            }
    
    def get_telemetry_all_drones(self) -> List[Dict]:
        """Get current telemetry for all drones.
        
        Returns:
            List of telemetry dictionaries
        """
        telemetry_list = []
        for drone_id, state in self.drone_states.items():
            telemetry = self._get_drone_telemetry(drone_id, state)
            telemetry_list.append(telemetry)
        return telemetry_list
    
    def get_telemetry_single_drone(self, drone_id: str) -> Dict:
        """Get telemetry for a single drone.
        
        Args:
            drone_id: Drone identifier
            
        Returns:
            Telemetry dictionary
        """
        if drone_id not in self.drone_states:
            return None
        
        state = self.drone_states[drone_id]
        return self._get_drone_telemetry(drone_id, state)
    
    def _get_drone_telemetry(self, drone_id: str, state: Dict) -> Dict:
        """Get telemetry for a drone, updating its position.
        
        Args:
            drone_id: Drone ID
            state: Drone state dictionary
            
        Returns:
            Telemetry dictionary
        """
        # Update position based on velocity
        # Rough conversion: 1 degree lat ≈ 111 km, 1 degree lon ≈ 111 km * cos(lat)
        lat_per_ms = 1.0 / (111000) * 0.25  # 0.25 second update interval
        lon_per_ms = 1.0 / (111000 * math.cos(math.radians(state["latitude"]))) * 0.25
        
        state["latitude"] += state["velocity_y_ms"] * lat_per_ms
        state["longitude"] += state["velocity_x_ms"] * lon_per_ms
        state["altitude_msl"] += state["velocity_z_ms"] * 0.25
        
        # Keep within Bengaluru bounds
        state["latitude"] = max(12.85, min(13.15, state["latitude"]))
        state["longitude"] = max(77.45, min(77.75, state["longitude"]))
        state["altitude_msl"] = max(900, min(1150, state["altitude_msl"]))
        
        # Random walk for velocities (slight drift)
        state["velocity_x_ms"] += random.uniform(-0.5, 0.5)
        state["velocity_y_ms"] += random.uniform(-0.5, 0.5)
        state["velocity_z_ms"] += random.uniform(-0.1, 0.1)
        
        # Clamp velocities
        state["velocity_x_ms"] = max(-15, min(15, state["velocity_x_ms"]))
        state["velocity_y_ms"] = max(-15, min(15, state["velocity_y_ms"]))
        state["velocity_z_ms"] = max(-5, min(5, state["velocity_z_ms"]))
        
        # Battery drain (small amount per update)
        state["battery_percent"] -= random.uniform(0.01, 0.05)
        state["battery_percent"] = max(0, state["battery_percent"])
        
        # Recalculate heading from velocity
        state["heading_deg"] = math.degrees(math.atan2(
            state["velocity_x_ms"],
            state["velocity_y_ms"]
        )) % 360
        
        # Speed
        speed_ms = math.sqrt(
            state["velocity_x_ms"]**2 +
            state["velocity_y_ms"]**2 +
            state["velocity_z_ms"]**2
        )
        
        return {
            "telemetry_id": f"TEL_{drone_id}_{int(datetime.utcnow().timestamp() * 1000)}",
            "drone_id": drone_id,
            "flight_id": state.get("flight_id"),
            "latitude": state["latitude"],
            "longitude": state["longitude"],
            "altitude_msl": state["altitude_msl"],
            "velocity_x_ms": state["velocity_x_ms"],
            "velocity_y_ms": state["velocity_y_ms"],
            "velocity_z_ms": state["velocity_z_ms"],
            "speed_ms": speed_ms,
            "heading_deg": state["heading_deg"],
            "pitch_deg": state["pitch_deg"],
            "roll_deg": state["roll_deg"],
            "yaw_deg": state["yaw_deg"],
            "battery_percent": state["battery_percent"],
            "voltage_v": 14.8,
            "current_a": 15.0 + random.uniform(-5, 5),
            "gps_satellites": state["gps_satellites"],
            "gps_hdop": round(random.uniform(0.8, 1.2), 2),
            "signal_strength_db": state["signal_strength_db"],
            "armed": state["armed"],
            "mode": state["mode"],
            "system_health": "OK",
            "gyro_temp_c": 45.0 + random.uniform(-2, 2),
            "baro_temp_c": 28.0 + random.uniform(-1, 1),
            "created_at": datetime.utcnow().isoformat(),
        }
    
    def update_drone_flight(self, drone_id: str, flight_id: str, latitude: float, longitude: float, altitude_msl: float):
        """Update drone state to follow a flight path.
        
        Args:
            drone_id: Drone ID
            flight_id: Flight ID
            latitude: Target latitude
            longitude: Target longitude
            altitude_msl: Target altitude MSL
        """
        if drone_id in self.drone_states:
            state = self.drone_states[drone_id]
            state["flight_id"] = flight_id
            state["armed"] = "true"
            state["mode"] = "AUTO"
            
            # Set velocity towards target
            dlat = latitude - state["latitude"]
            dlon = longitude - state["longitude"]
            dalt = altitude_msl - state["altitude_msl"]
            
            # Normalize velocity to ~15 m/s horizontal speed
            distance = math.sqrt(dlat**2 + dlon**2)
            if distance > 0:
                scale = 15.0 / (111000)  # Convert m/s to degrees/s
                state["velocity_y_ms"] = dlat * scale * 100
                state["velocity_x_ms"] = dlon * scale * 100
            
            state["velocity_z_ms"] = min(5.0, dalt / 10.0)  # Climb rate
    
    def land_drone(self, drone_id: str):
        """Land a drone (set velocity to 0, lower altitude).
        
        Args:
            drone_id: Drone ID
        """
        if drone_id in self.drone_states:
            state = self.drone_states[drone_id]
            state["velocity_x_ms"] = 0
            state["velocity_y_ms"] = 0
            state["velocity_z_ms"] = -2.0  # Descent rate
            state["armed"] = "false"
            state["mode"] = "LAND"
    
    def emergency_rth(self, drone_id: str, home_lat: float, home_lon: float, home_alt: float):
        """Initiate Return-to-Home for a drone.
        
        Args:
            drone_id: Drone ID
            home_lat: Home latitude
            home_lon: Home longitude
            home_alt: Home altitude MSL
        """
        if drone_id in self.drone_states:
            state = self.drone_states[drone_id]
            
            # Calculate velocity towards home
            dlat = home_lat - state["latitude"]
            dlon = home_lon - state["longitude"]
            dalt = home_alt - state["altitude_msl"]
            
            distance = math.sqrt(dlat**2 + dlon**2)
            if distance > 0:
                scale = 20.0 / (111000)  # RTH speed = 20 m/s
                state["velocity_y_ms"] = dlat * scale * 100
                state["velocity_x_ms"] = dlon * scale * 100
            
            # Climb to safe altitude first
            state["velocity_z_ms"] = min(8.0, dalt / 5.0)
            state["mode"] = "RTH"
