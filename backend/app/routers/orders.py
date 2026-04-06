"""Orders router."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from ..database import get_db
from ..models.order import Order
from ..models.delivery_node import DeliveryNode
from pydantic import BaseModel
import json
import uuid

router = APIRouter(prefix="/orders", tags=["orders"])


class WaypointSchema(BaseModel):
    """Waypoint schema."""
    latitude: float
    longitude: float
    altitude_msl: float
    order: int = 0


class OrderResponse(BaseModel):
    """Order response schema."""
    order_id: str
    destination_node_id: str
    payload_weight_kg: float
    status: str
    assigned_drone_id: str
    estimated_distance_m: float
    estimated_duration_s: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    """Order create schema."""
    destination_node_id: str
    payload_weight_kg: float
    payload_description: str = None


class OrderUpdate(BaseModel):
    """Order update schema."""
    status: str = None
    assigned_drone_id: str = None


@router.get("", response_model=List[OrderResponse])
async def list_orders(
    status: str = None,
    db: Session = Depends(get_db)
):
    """List all orders, optionally filtered by status."""
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    orders = query.order_by(Order.created_at.desc()).all()
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db: Session = Depends(get_db)):
    """Get specific order details."""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        return {"error": "Order not found"}
    return order


@router.post("", response_model=OrderResponse)
async def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    """Create a new order."""
    # Verify destination node exists
    node = db.query(DeliveryNode).filter(
        DeliveryNode.node_id == data.destination_node_id
    ).first()
    if not node:
        return {"error": "Delivery node not found"}
    
    # Check payload capacity
    if data.payload_weight_kg > node.max_payload_kg:
        return {
            "error": f"Payload {data.payload_weight_kg}kg exceeds node capacity {node.max_payload_kg}kg"
        }
    
    order = Order(
        order_id=f"ORD_{uuid.uuid4().hex[:12].upper()}",
        destination_node_id=data.destination_node_id,
        payload_weight_kg=data.payload_weight_kg,
        payload_description=data.payload_description,
        status="placed",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: str,
    data: OrderUpdate,
    db: Session = Depends(get_db)
):
    """Update order status."""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        return {"error": "Order not found"}
    
    if data.status:
        order.status = data.status
        if data.status == "delivered":
            order.delivered_at = datetime.utcnow()
    
    if data.assigned_drone_id:
        order.assigned_drone_id = data.assigned_drone_id
        order.assigned_at = datetime.utcnow()
    
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/assign-route")
async def assign_route_to_order(
    order_id: str,
    waypoints: List[WaypointSchema],
    distance_m: float,
    duration_s: float,
    db: Session = Depends(get_db)
):
    """Assign a planned route to an order."""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        return {"error": "Order not found"}
    
    # Store waypoints as JSON
    order.route_json = json.dumps([wp.dict() for wp in waypoints])
    order.estimated_distance_m = distance_m
    order.estimated_duration_s = duration_s
    order.status = "assigned"
    
    db.commit()
    db.refresh(order)
    return {
        "order_id": order.order_id,
        "status": order.status,
        "route_waypoints": len(waypoints),
        "estimated_distance_m": order.estimated_distance_m,
        "estimated_duration_s": order.estimated_duration_s,
    }
