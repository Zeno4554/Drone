from sqlalchemy import Column, String, Text, Float, DateTime, func
from geoalchemy2 import Geometry
from datetime import datetime
from .base import Base


class Obstacle(Base):
    """Obstacle model for buildings, trees, and other physical obstructions."""
    
    __tablename__ = "obstacles"
    
    obstacle_id = Column(String(64), primary_key=True, index=True)
    obstacle_name = Column(Text, nullable=True)
    
    # Obstacle type: building, tree, crane, power_line, antenna, other
    obstacle_type = Column(String(32), nullable=False)
    
    # Base location: (Latitude, Longitude)
    base_location = Column(Geometry("POINT", srid=4326), nullable=False)
    
    # Height properties
    base_elev_msl = Column(Float, nullable=False)  # Ground elevation
    top_elev_msl = Column(Float, nullable=False)  # Top of obstacle
    height_m = Column(Float, nullable=False)  # Obstacle height
    
    # Footprint polygon (optional, for complex shapes)
    footprint = Column(Geometry("POLYGON", srid=4326), nullable=True)
    
    # Bounding box (AABB for quick collision detection)
    min_lat = Column(Float, nullable=False)
    max_lat = Column(Float, nullable=False)
    min_lon = Column(Float, nullable=False)
    max_lon = Column(Float, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Obstacle {self.obstacle_id}: {self.obstacle_type}>"
