"""Delivery nodes router."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.delivery_node import DeliveryNode
from pydantic import BaseModel

router = APIRouter(prefix="/nodes", tags=["delivery_nodes"])


class DeliveryNodeResponse(BaseModel):
    """Delivery node response schema."""
    node_id: str
    building_id: str
    node_name: str
    altitude_msl: float
    height_agl: float
    node_type: str
    marker_id: str
    max_payload_kg: float
    
    class Config:
        from_attributes = True


class DeliveryNodeCreate(BaseModel):
    """Delivery node create schema."""
    node_id: str
    building_id: str
    node_name: str
    latitude: float
    longitude: float
    altitude_msl: float
    height_agl: float
    node_type: str = "rooftop"
    marker_id: str = None
    max_payload_kg: float = 2.0


@router.get("", response_model=List[DeliveryNodeResponse])
async def list_nodes(db: Session = Depends(get_db)):
    """List all delivery nodes."""
    nodes = db.query(DeliveryNode).all()
    return nodes


@router.get("/building/{building_id}", response_model=List[DeliveryNodeResponse])
async def get_nodes_by_building(building_id: str, db: Session = Depends(get_db)):
    """Get delivery nodes for a specific building."""
    nodes = db.query(DeliveryNode).filter(
        DeliveryNode.building_id == building_id
    ).all()
    return nodes


@router.get("/{node_id}", response_model=DeliveryNodeResponse)
async def get_node(node_id: str, db: Session = Depends(get_db)):
    """Get specific delivery node details."""
    node = db.query(DeliveryNode).filter(DeliveryNode.node_id == node_id).first()
    if not node:
        return {"error": "Node not found"}
    return node


@router.post("", response_model=DeliveryNodeResponse)
async def create_node(data: DeliveryNodeCreate, db: Session = Depends(get_db)):
    """Create a new delivery node."""
    node = DeliveryNode(
        node_id=data.node_id,
        building_id=data.building_id,
        node_name=data.node_name,
        altitude_msl=data.altitude_msl,
        height_agl=data.height_agl,
        node_type=data.node_type,
        marker_id=data.marker_id,
        max_payload_kg=data.max_payload_kg,
        location=f"POINTZ({data.longitude} {data.latitude} {data.altitude_msl})",
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node
