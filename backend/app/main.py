"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from .config import settings
from .database import init_db
from .routers import buildings, delivery_nodes, orders, routes, map, telemetry, setup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="3D Drone Delivery Navigation System",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(buildings.router, prefix=settings.API_V1_PREFIX)
app.include_router(delivery_nodes.router, prefix=settings.API_V1_PREFIX)
app.include_router(orders.router, prefix=settings.API_V1_PREFIX)
app.include_router(routes.router, prefix=settings.API_V1_PREFIX)
app.include_router(map.router, prefix=settings.API_V1_PREFIX)
app.include_router(telemetry.router, prefix=settings.API_V1_PREFIX)
app.include_router(setup.router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("🚀 Starting AeroCorridor Backend")
    
    # Detect database mode
    is_supabase = settings.SUPABASE_MODE or "supabase.co" in settings.DATABASE_URL
    if is_supabase:
        db_mode = "🔒 Supabase (Managed PostgreSQL + PostGIS)"
        pool_info = f"Connection pool: {settings.DB_POOL_SIZE} (Supabase optimized)"
    else:
        db_mode = "📡 Local PostgreSQL"
        pool_info = f"Connection pool: {settings.DB_POOL_SIZE}"
    
    logger.info(f"Database Mode: {db_mode}")
    logger.info(f"Database URL: {settings.DATABASE_URL[:50]}...")
    logger.info(pool_info)
    logger.info(f"API Endpoint: {settings.API_V1_PREFIX}")
    
    try:
        init_db()
        logger.info("✅ Database connected and initialized successfully")
        if is_supabase:
            logger.info("✨ PostGIS extensions available on Supabase")
        
        if settings.AUTO_BOOTSTRAP:
            from .services.demo_bootstrap import ensure_demo_data
            from .database import SessionLocal
            db = SessionLocal()
            try:
                counts = ensure_demo_data(db)
                if counts.get("skipped"):
                    logger.info("⏭️ Demo data already present — skipped bootstrap")
                else:
                    logger.info(f"🌱 Demo data bootstrapped: {counts}")
            finally:
                db.close()
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "api_docs": "/docs",
        "api_url": f"{settings.API_V1_PREFIX}",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
    }


@app.get("/api/v1")
async def api_root():
    """API v1 root with available endpoints."""
    return {
        "version": "1.0",
        "endpoints": {
            "buildings": "/api/v1/buildings",
            "delivery_nodes": "/api/v1/nodes",
            "orders": "/api/v1/orders",
            "route_planning": "/api/v1/routes",
            "map_data": "/api/v1/map",
            "telemetry": "/api/v1/telemetry",
        },
        "setup": "/api/v1/setup",
        "websockets": {
            "telemetry_stream": "/api/v1/telemetry/ws",
        },
    }


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
        },
    )
