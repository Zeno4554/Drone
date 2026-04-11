"""Database seeding — thin CLI wrapper around demo_bootstrap.

Prefer using POST /api/v1/setup/bootstrap against a running server,
or rely on AUTO_BOOTSTRAP=true which seeds on first startup.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config import settings
from backend.app.models import Base
from backend.app.services.demo_bootstrap import ensure_demo_data

connect_args = {}
if settings.SUPABASE_MODE or "supabase.co" in settings.DATABASE_URL:
    connect_args["sslmode"] = "require"

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)


def main():
    db = SessionLocal()
    try:
        counts = ensure_demo_data(db)
        if counts.get("skipped"):
            print("⏭️  Demo data already present — nothing inserted.")
        else:
            print(f"🌱 Bootstrapped: {counts}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
