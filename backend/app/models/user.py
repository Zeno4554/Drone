from sqlalchemy import Column, String, DateTime, Boolean
from datetime import datetime
from .base import Base


class User(Base):
    """User model for operators and admins."""
    
    __tablename__ = "users"
    
    user_id = Column(String(64), primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(128), unique=True, nullable=False)
    full_name = Column(String(128), nullable=False)
    
    # Role: operator, admin, viewer
    role = Column(String(32), nullable=False, default="operator")
    
    # Account status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<User {self.username}: {self.role}>"
