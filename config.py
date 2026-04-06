import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application configuration."""

    # Database (Supabase or PostgreSQL)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/aerocorridor"
    )

    # Supabase configuration
    SUPABASE_MODE: bool = True
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))

    # CORS
    CORS_ORIGINS: list = ["*"]

    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "AeroCorridor"
    VERSION: str = "2.0.0"

    # Route Planning
    VOXEL_SIZE_M: float = 5.0
    CRUISE_ALTITUDE_AGL_M: float = 100.0
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
