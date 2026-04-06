from sqlalchemy import Column, String, Text, Float, DateTime, func
from geoalchemy2 import Geometry
from datetime import datetime
from .base import Base


class Building(Base):
    """Building model for delivery destinations."""
    
    __tablename__ = "buildings"
    
    building_id = Column(String(64), primary_key=True, index=True)
    name = Column(Text, nullable=False)
    city = Column(Text, nullable=False, default="Bengaluru")
    description = Column(Text, nullable=True)
    
    # PostGIS geometry: (Latitude, Longitude)
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    
    # Terrain elevation in meters MSL (Mean Sea Level)
    ground_elev_msl = Column(Float, nullable=False)
    
    # Building height in meters
    height_m = Column(Float, nullable=False)
    
    # Top of building in MSL (ground_elev_msl + height_m)
    top_elev_msl = Column(Float, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Building {self.building_id}: {self.name}>"
