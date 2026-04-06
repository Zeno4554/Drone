from sqlalchemy import Column, String, Float, DateTime, Integer, Text
from geoalchemy2 import Geometry
from datetime import datetime
from .base import Base


class Telemetry(Base):
    """Real-time telemetry model for active drones."""
    
    __tablename__ = "telemetry"
    
    telemetry_id = Column(String(64), primary_key=True, index=True)
    drone_id = Column(String(64), nullable=False, index=True)
    flight_id = Column(String(64), nullable=True)
    
    # Position: (Latitude, Longitude, Altitude_MSL_meters)
    position = Column(Geometry("POINTZ", srid=4326), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude_msl = Column(Float, nullable=False)
    
    # Velocity
    velocity_x_ms = Column(Float, default=0.0)  # East
    velocity_y_ms = Column(Float, default=0.0)  # North
    velocity_z_ms = Column(Float, default=0.0)  # Up
    speed_ms = Column(Float, default=0.0)
    heading_deg = Column(Float, default=0.0)  # Compass bearing
    
    # Pitch, Roll, Yaw (Euler angles in degrees)
    pitch_deg = Column(Float, default=0.0)
    roll_deg = Column(Float, default=0.0)
    yaw_deg = Column(Float, default=0.0)
    
    # Power & Battery
    battery_percent = Column(Float, nullable=False)
    voltage_v = Column(Float, nullable=True)
    current_a = Column(Float, nullable=True)
    
    # Health
    gps_satellites = Column(Integer, default=0)
    gps_hdop = Column(Float, nullable=True)  # Horizontal dilution of precision
    signal_strength_db = Column(Float, nullable=True)  # Radio signal strength
    
    # Status
    armed = Column(String(16), default="false")
    mode = Column(String(32), default="STABILIZE")  # STABILIZE, AUTO, RTH, etc.
    system_health = Column(String(64), nullable=True)  # JSON health status
    
    # Temperature
    gyro_temp_c = Column(Float, nullable=True)
    baro_temp_c = Column(Float, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<Telemetry {self.drone_id}: alt={self.altitude_msl}m, bat={self.battery_percent}%>"
