"""Map data router (GeoJSON generation)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.building import Building
from ..models.delivery_node import DeliveryNode
from ..models.risk_voxel import RiskVoxel
from ..models.obstacle import Obstacle
from ..services.risk_calculator import RiskCalculator

router = APIRouter(prefix="/map", tags=["map"])
risk_calc = RiskCalculator()


@router.get("/buildings/geojson")
async def get_buildings_geojson(db: Session = Depends(get_db)):
    """Get all buildings as GeoJSON FeatureCollection."""
    buildings = db.query(Building).all()
    
    features = []
    for b in buildings:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [b.location.x, b.location.y],  # [lon, lat]
            },
            "properties": {
                "building_id": b.building_id,
                "name": b.name,
                "height_m": b.height_m,
                "ground_elev_msl": b.ground_elev_msl,
                "top_elev_msl": b.top_elev_msl,
            },
        }
        features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/nodes/geojson")
async def get_delivery_nodes_geojson(db: Session = Depends(get_db)):
    """Get all delivery nodes as GeoJSON FeatureCollection."""
    nodes = db.query(DeliveryNode).all()
    
    features = []
    for node in nodes:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [node.location.x, node.location.y],
            },
            "properties": {
                "node_id": node.node_id,
                "node_name": node.node_name,
                "altitude_msl": node.altitude_msl,
                "height_agl": node.height_agl,
                "node_type": node.node_type,
                "marker_id": node.marker_id,
            },
        }
        features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/risk-zones/geojson")
async def get_risk_zones_geojson(
    db: Session = Depends(get_db),
    min_risk: float = Query(0.0, ge=0.0, le=1.0),
):
    """Get risk voxels as GeoJSON FeatureCollection.
    
    Each voxel represented as a grid point colored by risk level.
    """
    # Query risk voxels above minimum threshold
    risk_voxels = db.query(RiskVoxel).filter(
        RiskVoxel.composite_risk >= min_risk
    ).all()
    
    features = []
    for voxel in risk_voxels:
        danger_colors = {
            "green": "#00ff00",
            "grey": "#808080",
            "yellow": "#ffff00",
            "red": "#ff0000",
            "black": "#000000",
        }
        
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [voxel.center.x, voxel.center.y],
            },
            "properties": {
                "voxel_id": voxel.voxel_id,
                "risk_score": voxel.composite_risk,
                "zone_color": voxel.zone_color,
                "danger_hex": danger_colors.get(voxel.zone_color, "#808080"),
                "altitude_msl": voxel.center.z,
                "success_rate": voxel.flight_success_rate,
            },
        }
        features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/obstacles/geojson")
async def get_obstacles_geojson(db: Session = Depends(get_db)):
    """Get all obstacles as GeoJSON FeatureCollection."""
    obstacles = db.query(Obstacle).all()
    
    features = []
    for obs in obstacles:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [obs.base_location.x, obs.base_location.y],
            },
            "properties": {
                "obstacle_id": obs.obstacle_id,
                "type": obs.obstacle_type,
                "height_m": obs.height_m,
                "base_elev_msl": obs.base_elev_msl,
                "top_elev_msl": obs.top_elev_msl,
            },
        }
        features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.post("/risk-heatmap")
async def generate_risk_heatmap(
    min_lat: float = 12.85,
    max_lat: float = 13.15,
    min_lon: float = 77.45,
    max_lon: float = 77.75,
    min_alt_msl: float = 920.0,
    max_alt_msl: float = 1050.0,
    grid_size: int = 5,
):
    """Generate risk heatmap for a geographic area.
    
    Returns 3D grid of voxels with risk scores.
    """
    bounds = {
        "min_lat": min_lat,
        "max_lat": max_lat,
        "min_lon": min_lon,
        "max_lon": max_lon,
        "min_alt": min_alt_msl,
        "max_alt": max_alt_msl,
    }
    
    voxels = risk_calc.generate_risk_heatmap(bounds, grid_size=grid_size)
    
    # Convert to GeoJSON format
    features = []
    for voxel in voxels:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [voxel["longitude"], voxel["latitude"]],
            },
            "properties": {
                "risk_score": voxel["risk_score"],
                "zone_color": voxel["zone_color"],
                "altitude_msl": voxel["altitude_msl"],
            },
        }
        features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/bounds")
async def get_map_bounds():
    """Get recommended map bounds for Bengaluru operation zone."""
    return {
        "bounds": {
            "north": 13.15,
            "south": 12.85,
            "east": 77.75,
            "west": 77.45,
        },
        "center": {
            "latitude": 13.0,
            "longitude": 77.6,
        },
        "zoom_default": 12,
    }
