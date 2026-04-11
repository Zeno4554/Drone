"""Drone assignment logic — battery + availability based selection."""

from typing import Optional, Dict
from sqlalchemy.orm import Session

from ..models.order import Order
from ..models.delivery_node import DeliveryNode
from ..routers.telemetry import telemetry_simulator


def assign_drone_to_order(order_id: str, db: Session) -> Dict:
    """Select the best drone for an order and dispatch it toward the destination.

    Returns a dict with assignment result or raises ValueError on failure.
    """
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise ValueError("Order not found")

    if order.assigned_drone_id:
        return {
            "order_id": order.order_id,
            "drone_id": order.assigned_drone_id,
            "status": order.status,
            "already_assigned": True,
        }

    node = db.query(DeliveryNode).filter(
        DeliveryNode.node_id == order.destination_node_id
    ).first()
    if not node:
        raise ValueError("Destination node not found")

    drone_id = telemetry_simulator.select_best_drone(order.payload_weight_kg)
    if not drone_id:
        raise ValueError("No available drone with sufficient battery/payload capacity")

    telemetry_simulator.mark_drone_busy(drone_id, order.order_id)

    from sqlalchemy import func
    dest_lon = db.scalar(func.ST_X(node.location))
    dest_lat = db.scalar(func.ST_Y(node.location))
    dest_alt = node.altitude_msl

    flight_id = f"FL_{order.order_id}"
    telemetry_simulator.update_drone_flight(
        drone_id, flight_id, dest_lat, dest_lon, dest_alt
    )

    from datetime import datetime
    order.assigned_drone_id = drone_id
    order.assigned_at = datetime.utcnow()
    order.status = "assigned"
    db.commit()
    db.refresh(order)

    return {
        "order_id": order.order_id,
        "drone_id": drone_id,
        "status": order.status,
        "already_assigned": False,
        "destination": {"lat": dest_lat, "lon": dest_lon, "alt_msl": dest_alt},
    }


def release_drone_for_order(order_id: str, db: Session) -> bool:
    """Release the drone assigned to an order (after delivery/cancellation)."""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order or not order.assigned_drone_id:
        return False
    telemetry_simulator.release_drone(order.assigned_drone_id)
    return True
