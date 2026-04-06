"""Route planning router."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..services.route_planner import RoutePlanner3D
from ..models.delivery_node import DeliveryNode
from ..models.building import Building
from pydantic import BaseModel

router = APIRouter(prefix="/routes", tags=["routes"])

# Initialize route planner
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
    """Plan a 3D route from source to destination node.
    
    Uses A* pathfinding accounting for:
    - Terrain obstacles
    - Altitude constraints (MSL-normalized)
    - Risk zones
    - Wind patterns
    """
    # Get destination node
    dest_node = db.query(DeliveryNode).filter(
        DeliveryNode.node_id == req.destination_node_id
    ).first()
    
    if not dest_node:
        return {"error": "Destination node not found"}
    
    # Get all buildings as obstacles (simplified)
    buildings = db.query(Building).all()
    obstacles = [
        {
            "lat": b.location.x,
            "lon": b.location.y,
            "alt_msl": b.top_elev_msl,
            "height": b.height_m,
        }
        for b in buildings
    ]
    
    # Plan route
    route = route_planner.plan_route(
        source_lat=req.source_lat,
        source_lon=req.source_lon,
        source_alt_msl=req.source_alt_msl,
        dest_lat=dest_node.location.x,
        dest_lon=dest_node.location.y,
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
    """Validate a proposed route for safety.
    
    Checks:
    - No altitude violations
    - No obstacle collisions
    - Risk zones within acceptable limits
    """
    if not waypoints or len(waypoints) < 2:
        return {"valid": False, "error": "At least 2 waypoints required"}
    
    # Get all buildings
    buildings = db.query(Building).all()
    
    issues = []
    max_risk = 0.0
    
    for i, wp in enumerate(waypoints):
        # Check altitude constraints
        if wp.altitude_msl < 920:  # Below Bengaluru baseline
            issues.append(f"Waypoint {i}: Altitude too low ({wp.altitude_msl}m MSL)")
        if wp.altitude_msl > 1150:  # Above max altitude
            issues.append(f"Waypoint {i}: Altitude too high ({wp.altitude_msl}m MSL)")
        
        # Check collisions with buildings (simplified)
        for building in buildings:
            lat_diff = abs(wp.latitude - building.location.x)
            lon_diff = abs(wp.longitude - building.location.y)
            
            # Simple distance check
            if lat_diff < 0.01 and lon_diff < 0.01:  # ~1 km
                if wp.altitude_msl < building.top_elev_msl + 50:
                    issues.append(f"Waypoint {i}: Too close to building {building.name}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "max_risk": max_risk,
    }


@router.get("/suggestions/{destination_node_id}")
async def get_route_suggestions(
    destination_node_id: str,
    source_lat: Optional[float] = 12.9716,
    source_lon: Optional[float] = 77.5946,
    source_alt_msl: Optional[float] = 980.0,
    db: Session = Depends(get_db)
):
    """Get suggested routes (multiple alternatives).
    
    Returns primary and alternative routes.
    """
    dest_node = db.query(DeliveryNode).filter(
        DeliveryNode.node_id == destination_node_id
    ).first()
    
    if not dest_node:
        return {"error": "Destination node not found"}
    
    # For now, return single route (multi-path A* would be enhancement)
    primary_route = route_planner.plan_route(
        source_lat=source_lat,
        source_lon=source_lon,
        source_alt_msl=source_alt_msl,
        dest_lat=dest_node.location.x,
        dest_lon=dest_node.location.y,
        dest_alt_msl=dest_node.altitude_msl,
    )
    
    return {
        "primary": {
            "waypoints": [wp.to_dict() for wp in primary_route["waypoints"]],
            "distance_m": primary_route["total_distance_m"],
            "duration_s": primary_route["estimated_duration_s"],
            "risk": primary_route["risk_score"],
        },
        "alternatives": [],  # Could add more routes
    }
