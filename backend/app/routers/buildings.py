"""Buildings router."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.building import Building
from pydantic import BaseModel

router = APIRouter(prefix="/buildings", tags=["buildings"])


class BuildingResponse(BaseModel):
    """Building response schema."""
    building_id: str
    name: str
    city: str
    ground_elev_msl: float
    height_m: float
    top_elev_msl: float
    
    class Config:
        from_attributes = True


class BuildingCreate(BaseModel):
    """Building create schema."""
    building_id: str
    name: str
    city: str = "Bengaluru"
    latitude: float
    longitude: float
    ground_elev_msl: float
    height_m: float


@router.get("", response_model=List[BuildingResponse])
async def list_buildings(db: Session = Depends(get_db)):
    """List all buildings."""
    buildings = db.query(Building).all()
    return buildings


@router.get("/{building_id}", response_model=BuildingResponse)
async def get_building(building_id: str, db: Session = Depends(get_db)):
    """Get specific building details."""
    building = db.query(Building).filter(Building.building_id == building_id).first()
    if not building:
        return {"error": "Building not found"}
    return building


@router.post("", response_model=BuildingResponse)
async def create_building(data: BuildingCreate, db: Session = Depends(get_db)):
    """Create a new building."""
    building = Building(
        building_id=data.building_id,
        name=data.name,
        city=data.city,
        ground_elev_msl=data.ground_elev_msl,
        height_m=data.height_m,
        top_elev_msl=data.ground_elev_msl + data.height_m,
        location=f"POINT({data.longitude} {data.latitude})",
    )
    db.add(building)
    db.commit()
    db.refresh(building)
    return building
