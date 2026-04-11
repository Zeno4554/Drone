"""Setup / bootstrap router — API-driven demo data management."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.building import Building
from ..models.delivery_node import DeliveryNode
from ..models.risk_voxel import RiskVoxel
from ..models.obstacle import Obstacle
from ..models.order import Order
from ..services.demo_bootstrap import ensure_demo_data, reseed_demo_data

router = APIRouter(prefix="/setup", tags=["setup"])


@router.post("/bootstrap")
async def bootstrap(db: Session = Depends(get_db)):
    """Insert demo data if the database is empty (idempotent)."""
    counts = ensure_demo_data(db)
    return counts


@router.post("/reseed")
async def reseed(db: Session = Depends(get_db)):
    """Clear all data and re-seed with nationwide demo data."""
    counts = reseed_demo_data(db)
    return counts


@router.get("/status")
async def status(db: Session = Depends(get_db)):
    """Return current row counts for core tables."""
    return {
        "buildings": db.query(Building).count(),
        "delivery_nodes": db.query(DeliveryNode).count(),
        "risk_voxels": db.query(RiskVoxel).count(),
        "obstacles": db.query(Obstacle).count(),
        "orders": db.query(Order).count(),
    }
