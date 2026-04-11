"""Route planning router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from ..database import get_db
from ..services.route_planner import RoutePlanner3D
from ..models.delivery_node import DeliveryNode
from ..models.building import Building
from pydantic import BaseModel

router = APIRouter(prefix="/routes", tags=["routes"])

route_planner = RoutePlanner3D()


class RouteRequest(BaseModel):
    """Route planning request."""
    source_lat: float
    source_lon: float
    source_alt_msl: float
    destination_node_id: str


class WaypointResponse(BaseModel):
    """Waypoint in route."""
    latitude: float
    longitude: float
    altitude_msl: float
    order: int


class RouteResponse(BaseModel):
    """Route planning response."""
    waypoints: List[WaypointResponse]
    total_distance_m: float
    total_altitude_change_m: float
    estimated_duration_s: float
    risk_score: float
    valid: bool


@router.post("", response_model=RouteResponse)
async def plan_route(req: RouteRequest, db: Session = Depends(get_db)):
    """Plan a 3D route from source to destination node."""
    dest_node = db.query(DeliveryNode).filter(
        DeliveryNode.node_id == req.destination_node_id
    ).first()

    if not dest_node:
        raise HTTPException(status_code=404, detail="Destination node not found")

    dest_lon = db.scalar(func.ST_X(dest_node.location))
    dest_lat = db.scalar(func.ST_Y(dest_node.location))

    buildings = db.query(Building).all()
    obstacles = []
    for b in buildings:
        b_lon = db.scalar(func.ST_X(b.location))
        b_lat = db.scalar(func.ST_Y(b.location))
        obstacles.append({
            "lat": b_lat, "lon": b_lon,
            "alt_msl": b.top_elev_msl, "height": b.height_m,
        })

    route = route_planner.plan_route(
        source_lat=req.source_lat,
        source_lon=req.source_lon,
        source_alt_msl=req.source_alt_msl,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        dest_alt_msl=dest_node.altitude_msl,
        obstacles=obstacles,
    )

    return {
        "waypoints": [wp.to_dict() for wp in route["waypoints"]],
        "total_distance_m": route["total_distance_m"],
        "total_altitude_change_m": route["total_altitude_change_m"],
        "estimated_duration_s": route["estimated_duration_s"],
        "risk_score": route["risk_score"],
        "valid": route["valid"],
    }


@router.post("/validate")
async def validate_route(
    waypoints: List[WaypointResponse],
    db: Session = Depends(get_db)
):
    """Validate a proposed route for safety."""
    if not waypoints or len(waypoints) < 2:
        return {"valid": False, "error": "At least 2 waypoints required"}

    buildings = db.query(Building).all()
    issues = []

    for i, wp in enumerate(waypoints):
        if wp.altitude_msl > 1500:
            issues.append(f"Waypoint {i}: Altitude too high ({wp.altitude_msl}m MSL)")

        for b in buildings:
            b_lat = db.scalar(func.ST_Y(b.location))
            b_lon = db.scalar(func.ST_X(b.location))
            if abs(wp.latitude - b_lat) < 0.01 and abs(wp.longitude - b_lon) < 0.01:
                if wp.altitude_msl < b.top_elev_msl + 50:
                    issues.append(f"Waypoint {i}: Too close to building {b.name}")

    return {"valid": len(issues) == 0, "issues": issues}


@router.get("/suggestions/{destination_node_id}")
async def get_route_suggestions(
    destination_node_id: str,
    source_lat: Optional[float] = 22.5,
    source_lon: Optional[float] = 78.9,
    source_alt_msl: Optional[float] = 300.0,
    db: Session = Depends(get_db)
):
    """Get suggested routes."""
    dest_node = db.query(DeliveryNode).filter(
        DeliveryNode.node_id == destination_node_id
    ).first()

    if not dest_node:
        raise HTTPException(status_code=404, detail="Destination node not found")

    dest_lon = db.scalar(func.ST_X(dest_node.location))
    dest_lat = db.scalar(func.ST_Y(dest_node.location))

    primary_route = route_planner.plan_route(
        source_lat=source_lat,
        source_lon=source_lon,
        source_alt_msl=source_alt_msl,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        dest_alt_msl=dest_node.altitude_msl,
    )

    return {
        "primary": {
            "waypoints": [wp.to_dict() for wp in primary_route["waypoints"]],
            "distance_m": primary_route["total_distance_m"],
            "duration_s": primary_route["estimated_duration_s"],
            "risk": primary_route["risk_score"],
        },
        "alternatives": [],
    }
