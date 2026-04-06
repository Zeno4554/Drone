from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from geoalchemy2 import Geometry
from .config import settings
from .models import Base
import ssl

# Prepare connection arguments
connect_args = {}

# For Supabase or production, use SSL
if settings.SUPABASE_MODE or "supabase.co" in settings.DATABASE_URL:
    # Supabase requires SSL
    connect_args["sslmode"] = "require"
    print("🔒 Using SSL connection (Supabase detected)")
else:
    print("📡 Using standard PostgreSQL connection")

# Create engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,  # Supabase recommends smaller pools
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def drop_all_tables():
    """Drop all tables (for testing/reset)."""
    Base.metadata.drop_all(bind=engine)
    print("🗑️  All tables dropped")
