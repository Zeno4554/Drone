import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application configuration."""
    
    # Database (Supabase or PostgreSQL)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/aerocorridor"
    )
    
    # Supabase configuration
    SUPABASE_MODE: bool = os.getenv("SUPABASE_MODE", "false").lower() == "true"
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))  # Supabase recommends smaller pools
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "AeroCorridor"
    VERSION: str = "2.0.0"
    
    # Route Planning
    VOXEL_SIZE_M: float = 5.0  # 5m x 5m x 5m voxels
    CRUISE_ALTITUDE_AGL_M: float = 100.0  # Above ground level
    MAX_ALTITUDE_AGL_M: float = 200.0
    
    # Telemetry
    TELEMETRY_UPDATE_INTERVAL_MS: int = 500
    DRONE_COUNT: int = 3
    
    # Bengaluru Baseline
    BENGALURU_GROUND_ELEV_MSL: float = 920.0
    
    # Simulation
    ENABLE_TELEMETRY_SIMULATION: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
