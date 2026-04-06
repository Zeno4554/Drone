from sqlalchemy import Column, String, Text, Float, DateTime, Integer
from datetime import datetime
from .base import Base


class FlightLog(Base):
    """Flight log model for completed/in-progress deliveries."""
    
    __tablename__ = "flight_logs"
    
    flight_id = Column(String(64), primary_key=True, index=True)
    order_id = Column(String(64), nullable=False)
    drone_id = Column(String(64), nullable=False)
    
    # Status: in-progress, completed, aborted, failed
    status = Column(String(32), nullable=False, default="in-progress")
    
    # Route taken
    route_json = Column(Text, nullable=True)  # JSON array of actual waypoints
    
    # Flight metrics
    total_distance_m = Column(Float, nullable=True)
    total_duration_s = Column(Float, nullable=True)
    max_altitude_msl = Column(Float, nullable=True)
    avg_speed_ms = Column(Float, nullable=True)
    battery_used_percent = Column(Float, nullable=True)
    
    # Weather conditions
    wind_speed_ms = Column(Float, nullable=True)
    wind_direction = Column(String(32), nullable=True)
    
    # Incidents
    incidents = Column(Text, nullable=True)  # JSON array of incidents
    num_collisions_avoided = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<FlightLog {self.flight_id}: {self.status}>"
