from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, func
from geoalchemy2 import Geometry
from datetime import datetime
from .base import Base


class DeliveryNode(Base):
    """Delivery node model (balcony, rooftop, gate, dock)."""
    
    __tablename__ = "delivery_nodes"
    
    node_id = Column(String(64), primary_key=True, index=True)
    building_id = Column(String(64), ForeignKey("buildings.building_id"), nullable=False)
    node_name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    
    # PostGIS geometry with Z: (Latitude, Longitude, Altitude_MSL)
    location = Column(Geometry("POINTZ", srid=4326), nullable=False)
    
    # MSL altitude (absolute height above sea level)
    altitude_msl = Column(Float, nullable=False)
    
    # AGL altitude (height above ground)
    height_agl = Column(Float, nullable=False)
    
    # Node type: balcony, rooftop, gate, dock, window
    node_type = Column(String(32), nullable=False, default="rooftop")
    
    # AprilTag marker ID for autonomous landing
    marker_id = Column(String(64), nullable=True)
    
    # Capacity constraints
    max_payload_kg = Column(Float, nullable=True)
    
    # Accessibility
    is_accessible = Column(String(32), nullable=False, default="true")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<DeliveryNode {self.node_id}: {self.node_name} @ {self.altitude_msl}m MSL>"
