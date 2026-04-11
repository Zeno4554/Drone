"""Telemetry WebSocket and real-time data router."""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Dict
import json
import asyncio
from datetime import datetime
from ..database import get_db
from ..models.telemetry import Telemetry
from ..models.flight_log import FlightLog
from ..services.telemetry_simulator import TelemetrySimulator
from pydantic import BaseModel

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

# Global telemetry simulator instance
telemetry_simulator = TelemetrySimulator(num_drones=5)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()


class TelemetryResponse(BaseModel):
    """Telemetry data response."""
    telemetry_id: str
    drone_id: str
    latitude: float
    longitude: float
    altitude_msl: float
    speed_ms: float
    heading_deg: float
    battery_percent: float
    armed: str
    mode: str
    created_at: str


@router.get("/current", response_model=List[TelemetryResponse])
async def get_current_telemetry():
    """Get current telemetry for all active drones (simulated)."""
    telemetry_list = telemetry_simulator.get_telemetry_all_drones()
    return telemetry_list


@router.get("/drone/{drone_id}")
async def get_drone_telemetry(drone_id: str):
    """Get current telemetry for a specific drone."""
    telemetry = telemetry_simulator.get_telemetry_single_drone(drone_id)
    if not telemetry:
        return {"error": "Drone not found"}
    return telemetry


@router.post("/record")
async def record_telemetry(
    drone_id: str,
    latitude: float,
    longitude: float,
    altitude_msl: float,
    battery_percent: float,
    db: Session = Depends(get_db)
):
    """Record telemetry point to database (for flight history)."""
    telemetry = Telemetry(
        telemetry_id=f"TEL_{drone_id}_{int(datetime.utcnow().timestamp() * 1000)}",
        drone_id=drone_id,
        latitude=latitude,
        longitude=longitude,
        altitude_msl=altitude_msl,
        battery_percent=battery_percent,
        armed="true",
        mode="AUTO",
        position=f"POINTZ({longitude} {latitude} {altitude_msl})",
    )
    db.add(telemetry)
    db.commit()
    return {"recorded": True}


@router.post("/drone/{drone_id}/assign-flight")
async def assign_flight_to_drone(
    drone_id: str,
    flight_id: str,
    destination_lat: float,
    destination_lon: float,
    destination_alt_msl: float,
):
    """Assign a flight path to a drone."""
    telemetry_simulator.update_drone_flight(
        drone_id,
        flight_id,
        destination_lat,
        destination_lon,
        destination_alt_msl,
    )
    return {"assigned": True, "drone_id": drone_id, "flight_id": flight_id}


@router.post("/drone/{drone_id}/emergency-rth")
async def emergency_return_to_home(
    drone_id: str,
    home_lat: float = 12.9716,
    home_lon: float = 77.5946,
    home_alt_msl: float = 950.0,
):
    """Trigger emergency Return-to-Home for a drone."""
    telemetry_simulator.emergency_rth(drone_id, home_lat, home_lon, home_alt_msl)
    return {"rth_initiated": True, "drone_id": drone_id}


@router.post("/drone/{drone_id}/land")
async def land_drone(drone_id: str):
    """Command drone to land."""
    telemetry_simulator.land_drone(drone_id)
    return {"land_initiated": True, "drone_id": drone_id}


@router.websocket("/ws")
async def websocket_telemetry_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time telemetry streaming.

    Each client receives its own 500 ms push loop (no redundant broadcast storm).
    """
    await manager.connect(websocket)
    try:
        while True:
            telemetry_list = telemetry_simulator.get_telemetry_all_drones()
            await websocket.send_json({
                "type": "telemetry_update",
                "timestamp": datetime.utcnow().isoformat(),
                "drones": telemetry_list,
            })
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@router.get("/flights/{drone_id}", response_model=List[Dict])
async def get_drone_flight_history(
    drone_id: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get flight history for a drone."""
    flights = db.query(FlightLog).filter(
        FlightLog.drone_id == drone_id
    ).order_by(
        FlightLog.created_at.desc()
    ).limit(limit).all()
    
    return [
        {
            "flight_id": f.flight_id,
            "order_id": f.order_id,
            "status": f.status,
            "distance_m": f.total_distance_m,
            "duration_s": f.total_duration_s,
            "battery_used": f.battery_used_percent,
            "created_at": f.created_at.isoformat(),
        }
        for f in flights
    ]


@router.post("/flights/{flight_id}/record-position")
async def record_flight_position(
    flight_id: str,
    drone_id: str,
    latitude: float,
    longitude: float,
    altitude_msl: float,
    battery_percent: float,
    db: Session = Depends(get_db),
):
    """Record a position point for an active flight."""
    # Find flight
    flight = db.query(FlightLog).filter(FlightLog.flight_id == flight_id).first()
    if not flight:
        return {"error": "Flight not found"}
    
    # Record telemetry
    telemetry = Telemetry(
        telemetry_id=f"TEL_{drone_id}_{int(datetime.utcnow().timestamp() * 1000)}",
        drone_id=drone_id,
        flight_id=flight_id,
        latitude=latitude,
        longitude=longitude,
        altitude_msl=altitude_msl,
        battery_percent=battery_percent,
        armed="true",
        mode="AUTO",
        position=f"POINTZ({longitude} {latitude} {altitude_msl})",
    )
    db.add(telemetry)
    
    # Update flight max altitude
    if not flight.max_altitude_msl or altitude_msl > flight.max_altitude_msl:
        flight.max_altitude_msl = altitude_msl
    
    db.commit()
    return {"recorded": True}
