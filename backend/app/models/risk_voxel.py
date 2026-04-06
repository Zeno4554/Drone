from sqlalchemy import Column, String, Float, DateTime, func
from geoalchemy2 import Geometry
from datetime import datetime
from .base import Base


class RiskVoxel(Base):
    """Risk voxel model for 3D risk mapping."""
    
    __tablename__ = "risk_voxels"
    
    voxel_id = Column(String(64), primary_key=True, index=True)
    
    # Voxel center: (Latitude, Longitude, Altitude_MSL)
    center = Column(Geometry("POINTZ", srid=4326), nullable=False)
    
    # Risk score 0.0-1.0
    composite_risk = Column(Float, nullable=False, default=0.0)
    
    # Risk level: green (0-0.2), grey (0.2-0.4), yellow (0.4-0.6), red (0.6-0.8), black (0.8-1.0)
    zone_color = Column(String(16), nullable=False, default="green")
    
    # Risk sources
    obstacle_density = Column(Float, default=0.0)  # Building/terrain density
    air_traffic_density = Column(Float, default=0.0)  # Manned aircraft paths
    restricted_airspace = Column(Float, default=0.0)  # Military/airport zones
    wind_factor = Column(Float, default=0.0)  # Wind hazard
    altitude_factor = Column(Float, default=0.0)  # Altitude-specific risks
    
    # Flight success metrics
    flight_success_rate = Column(Float, default=0.95)  # Historical success rate
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<RiskVoxel {self.voxel_id}: {self.zone_color} risk={self.composite_risk:.2f}>"
