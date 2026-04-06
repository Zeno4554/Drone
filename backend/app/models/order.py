from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey
from datetime import datetime
from .base import Base


class Order(Base):
    """Order model for drone deliveries."""
    
    __tablename__ = "orders"
    
    order_id = Column(String(64), primary_key=True, index=True)
    destination_node_id = Column(String(64), ForeignKey("delivery_nodes.node_id"), nullable=False)
    
    # Payload
    payload_weight_kg = Column(Float, nullable=False)
    payload_description = Column(Text, nullable=True)
    
    # Status: placed, assigned, in-transit, delivered, cancelled, failed
    status = Column(String(32), nullable=False, default="placed")
    
    # Assigned drone ID (once route is planned)
    assigned_drone_id = Column(String(64), nullable=True)
    
    # Route information
    route_json = Column(Text, nullable=True)  # JSON array of waypoints
    estimated_distance_m = Column(Float, nullable=True)
    estimated_duration_s = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    assigned_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Order {self.order_id}: {self.status}>"
