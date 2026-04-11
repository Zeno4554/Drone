"""Orders router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
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
    assigned_drone_id: Optional[str] = None
    estimated_distance_m: Optional[float] = None
    estimated_duration_s: Optional[float] = None
    route_json: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    """Order create schema."""
    destination_node_id: str
    payload_weight_kg: float
    payload_description: Optional[str] = None


class OrderUpdate(BaseModel):
    """Order update schema."""
    status: Optional[str] = None
    assigned_drone_id: Optional[str] = None


# ================= GET ALL ORDERS =================
@router.get("", response_model=List[OrderResponse])
async def list_orders(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)

    orders = query.order_by(Order.created_at.desc()).all()
    return orders


# ================= GET SINGLE ORDER =================
@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return order


# ================= CREATE ORDER =================
@router.post("", response_model=OrderResponse)
async def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    # Verify destination node exists
    node = db.query(DeliveryNode).filter(
        DeliveryNode.node_id == data.destination_node_id
    ).first()

    if not node:
        raise HTTPException(status_code=404, detail="Delivery node not found")

    # Check payload capacity
    if data.payload_weight_kg > node.max_payload_kg:
        raise HTTPException(
            status_code=400,
            detail=f"Payload {data.payload_weight_kg}kg exceeds node capacity {node.max_payload_kg}kg"
        )

    # Create order
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


# ================= UPDATE ORDER =================
@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: str,
    data: OrderUpdate,
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.order_id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

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


# ================= ASSIGN DRONE =================
@router.post("/{order_id}/assign-drone")
async def assign_drone(order_id: str, db: Session = Depends(get_db)):
    """Auto-assign the best available drone to an order (battery + availability)."""
    from ..services.drone_assignment import assign_drone_to_order
    try:
        result = assign_drone_to_order(order_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ================= ASSIGN ROUTE =================
@router.post("/{order_id}/assign-route")
async def assign_route_to_order(
    order_id: str,
    waypoints: List[WaypointSchema],
    distance_m: float,
    duration_s: float,
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.order_id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

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


# ================= RELEASE DRONE =================
@router.post("/{order_id}/release-drone")
async def release_drone(order_id: str, db: Session = Depends(get_db)):
    """Release the drone assigned to a delivered/cancelled order."""
    from ..services.drone_assignment import release_drone_for_order
    released = release_drone_for_order(order_id, db)
    if not released:
        raise HTTPException(status_code=400, detail="No drone assigned to release")
    return {"released": True, "order_id": order_id}