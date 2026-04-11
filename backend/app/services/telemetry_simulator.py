"""Telemetry simulation for drone tracking — nationwide India coverage."""

import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..config import settings

MIN_BATTERY_FOR_ASSIGNMENT = 25.0

# India bounds for clamping
INDIA_LAT_MIN, INDIA_LAT_MAX = 8.0, 35.0
INDIA_LON_MIN, INDIA_LON_MAX = 68.0, 97.0
ALT_MIN, ALT_MAX = 10, 1200


class TelemetrySimulator:
    """Simulates realistic drone telemetry data across India."""

    def __init__(self, num_drones: int = 5):
        self.num_drones = num_drones
        self.drone_states: Dict[str, Dict] = {}
        self._initialize_drones()

    def _initialize_drones(self):
        test_locations = [
            {"lat": 28.6315, "lon": 77.2167, "name": "Delhi"},
            {"lat": 19.0658, "lon": 72.8699, "name": "Mumbai"},
            {"lat": 12.9716, "lon": 77.5946, "name": "Bengaluru"},
            {"lat": 17.4435, "lon": 78.3772, "name": "Hyderabad"},
            {"lat": 13.0582, "lon": 80.2634, "name": "Chennai"},
        ]

        for i in range(self.num_drones):
            loc = test_locations[i % len(test_locations)]
            base_alt = loc.get("alt", 300)
            self.drone_states[f"DRONE_{i:03d}"] = {
                "drone_id": f"DRONE_{i:03d}",
                "latitude": loc["lat"] + random.uniform(-0.01, 0.01),
                "longitude": loc["lon"] + random.uniform(-0.01, 0.01),
                "altitude_msl": base_alt + random.uniform(20, 80),
                "velocity_x_ms": random.uniform(-5, 5),
                "velocity_y_ms": random.uniform(-5, 5),
                "velocity_z_ms": random.uniform(-1, 1),
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
                "max_payload_kg": 2.5,
                "available": True,
                "assigned_order_id": None,
                "home_city": loc["name"],
            }

    # ---- Assignment helpers ----

    def get_available_drones(self, min_payload_kg: float = 0.0) -> List[Dict]:
        candidates = []
        for drone_id, state in self.drone_states.items():
            if (
                state["available"]
                and state["battery_percent"] >= MIN_BATTERY_FOR_ASSIGNMENT
                and state["max_payload_kg"] >= min_payload_kg
                and state["mode"] not in ("LAND", "RTH")
            ):
                candidates.append(state)
        candidates.sort(key=lambda d: (-d["battery_percent"], d["drone_id"]))
        return candidates

    def select_best_drone(self, payload_kg: float) -> Optional[str]:
        candidates = self.get_available_drones(min_payload_kg=payload_kg)
        return candidates[0]["drone_id"] if candidates else None

    def mark_drone_busy(self, drone_id: str, order_id: str):
        if drone_id in self.drone_states:
            self.drone_states[drone_id]["available"] = False
            self.drone_states[drone_id]["assigned_order_id"] = order_id

    def release_drone(self, drone_id: str):
        if drone_id in self.drone_states:
            self.drone_states[drone_id]["available"] = True
            self.drone_states[drone_id]["assigned_order_id"] = None
            self.drone_states[drone_id]["flight_id"] = None

    def get_telemetry_all_drones(self) -> List[Dict]:
        telemetry_list = []
        for drone_id, state in self.drone_states.items():
            telemetry = self._get_drone_telemetry(drone_id, state)
            telemetry_list.append(telemetry)
        return telemetry_list

    def get_telemetry_single_drone(self, drone_id: str) -> Dict:
        if drone_id not in self.drone_states:
            return None
        state = self.drone_states[drone_id]
        return self._get_drone_telemetry(drone_id, state)

    def _get_drone_telemetry(self, drone_id: str, state: Dict) -> Dict:
        lat_per_ms = 1.0 / 111000 * 0.25
        lon_per_ms = 1.0 / (111000 * math.cos(math.radians(state["latitude"]))) * 0.25

        state["latitude"] += state["velocity_y_ms"] * lat_per_ms
        state["longitude"] += state["velocity_x_ms"] * lon_per_ms
        state["altitude_msl"] += state["velocity_z_ms"] * 0.25

        state["latitude"] = max(INDIA_LAT_MIN, min(INDIA_LAT_MAX, state["latitude"]))
        state["longitude"] = max(INDIA_LON_MIN, min(INDIA_LON_MAX, state["longitude"]))
        state["altitude_msl"] = max(ALT_MIN, min(ALT_MAX, state["altitude_msl"]))

        state["velocity_x_ms"] += random.uniform(-0.5, 0.5)
        state["velocity_y_ms"] += random.uniform(-0.5, 0.5)
        state["velocity_z_ms"] += random.uniform(-0.1, 0.1)

        state["velocity_x_ms"] = max(-15, min(15, state["velocity_x_ms"]))
        state["velocity_y_ms"] = max(-15, min(15, state["velocity_y_ms"]))
        state["velocity_z_ms"] = max(-5, min(5, state["velocity_z_ms"]))

        state["battery_percent"] -= random.uniform(0.01, 0.05)
        state["battery_percent"] = max(0, state["battery_percent"])

        state["heading_deg"] = math.degrees(math.atan2(
            state["velocity_x_ms"], state["velocity_y_ms"]
        )) % 360

        speed_ms = math.sqrt(
            state["velocity_x_ms"] ** 2 +
            state["velocity_y_ms"] ** 2 +
            state["velocity_z_ms"] ** 2
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
            "available": state.get("available", True),
            "assigned_order_id": state.get("assigned_order_id"),
            "max_payload_kg": state.get("max_payload_kg", 2.5),
            "home_city": state.get("home_city", ""),
            "created_at": datetime.utcnow().isoformat(),
        }

    def update_drone_flight(self, drone_id: str, flight_id: str, latitude: float, longitude: float, altitude_msl: float):
        if drone_id in self.drone_states:
            state = self.drone_states[drone_id]
            state["flight_id"] = flight_id
            state["armed"] = "true"
            state["mode"] = "AUTO"

            dlat = latitude - state["latitude"]
            dlon = longitude - state["longitude"]
            dalt = altitude_msl - state["altitude_msl"]

            distance = math.sqrt(dlat ** 2 + dlon ** 2)
            if distance > 0:
                scale = 15.0 / 111000
                state["velocity_y_ms"] = dlat * scale * 100
                state["velocity_x_ms"] = dlon * scale * 100

            state["velocity_z_ms"] = min(5.0, dalt / 10.0)

    def land_drone(self, drone_id: str):
        if drone_id in self.drone_states:
            state = self.drone_states[drone_id]
            state["velocity_x_ms"] = 0
            state["velocity_y_ms"] = 0
            state["velocity_z_ms"] = -2.0
            state["armed"] = "false"
            state["mode"] = "LAND"

    def emergency_rth(self, drone_id: str, home_lat: float, home_lon: float, home_alt: float):
        if drone_id in self.drone_states:
            state = self.drone_states[drone_id]

            dlat = home_lat - state["latitude"]
            dlon = home_lon - state["longitude"]
            dalt = home_alt - state["altitude_msl"]

            distance = math.sqrt(dlat ** 2 + dlon ** 2)
            if distance > 0:
                scale = 20.0 / 111000
                state["velocity_y_ms"] = dlat * scale * 100
                state["velocity_x_ms"] = dlon * scale * 100

            state["velocity_z_ms"] = min(8.0, dalt / 5.0)
            state["mode"] = "RTH"
