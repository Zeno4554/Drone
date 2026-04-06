"""Database seeding with test data."""

import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Base
from app.models.building import Building
from app.models.delivery_node import DeliveryNode
from app.models.order import Order
from app.models.risk_voxel import RiskVoxel
from app.models.obstacle import Obstacle

# Prepare connection arguments for Supabase or PostgreSQL
connect_args = {}
if settings.SUPABASE_MODE or "supabase.co" in settings.DATABASE_URL:
    connect_args["sslmode"] = "require"
    print("🔒 Connecting to Supabase...")
else:
    print("📡 Connecting to local PostgreSQL...")

# Create engine and tables
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()


def seed_buildings():
    """Seed Bengaluru test buildings."""
    buildings_data = [
        {
            "building_id": "BLD_PHOENIX_MALL",
            "name": "Phoenix Mall",
            "city": "Bengaluru",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "ground_elev_msl": 920.0,
            "height_m": 35.0,
        },
        {
            "building_id": "BLD_WHITEFIELD_TOWER",
            "name": "Whitefield Tech Tower",
            "city": "Bengaluru",
            "latitude": 12.9716,
            "longitude": 77.6412,
            "ground_elev_msl": 910.0,
            "height_m": 45.0,
        },
        {
            "building_id": "BLD_JAYANAGAR_COMPLEX",
            "name": "Jayanagar Commerce Complex",
            "city": "Bengaluru",
            "latitude": 12.9711,
            "longitude": 77.5532,
            "ground_elev_msl": 930.0,
            "height_m": 30.0,
        },
        {
            "building_id": "BLD_INDIRANAGAR_OFFICE",
            "name": "Indiranagar Business Park",
            "city": "Bengaluru",
            "latitude": 12.9700,
            "longitude": 77.6400,
            "ground_elev_msl": 915.0,
            "height_m": 50.0,
        },
        {
            "building_id": "BLD_KR_PURAM_RETAIL",
            "name": "KR Puram Retail Hub",
            "city": "Bengaluru",
            "latitude": 12.9680,
            "longitude": 77.6200,
            "ground_elev_msl": 925.0,
            "height_m": 25.0,
        },
    ]
    
    for b_data in buildings_data:
        building = Building(
            building_id=b_data["building_id"],
            name=b_data["name"],
            city=b_data["city"],
            location=f"POINT({b_data['longitude']} {b_data['latitude']})",
            ground_elev_msl=b_data["ground_elev_msl"],
            height_m=b_data["height_m"],
            top_elev_msl=b_data["ground_elev_msl"] + b_data["height_m"],
        )
        db.add(building)
    
    db.commit()
    print("✅ Seeded 5 buildings")


def seed_delivery_nodes():
    """Seed delivery nodes for buildings."""
    nodes_data = [
        # Phoenix Mall
        {
            "node_id": "NODE_PHX_ROOFTOP_1",
            "building_id": "BLD_PHOENIX_MALL",
            "node_name": "Phoenix Rooftop Main",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "altitude_msl": 955.0,
            "height_agl": 35.0,
            "node_type": "rooftop",
            "marker_id": "APR_001",
        },
        {
            "node_id": "NODE_PHX_BALCONY_1",
            "building_id": "BLD_PHOENIX_MALL",
            "node_name": "Phoenix Ground Level Dock",
            "latitude": 12.9715,
            "longitude": 77.5947,
            "altitude_msl": 922.0,
            "height_agl": 2.0,
            "node_type": "dock",
            "marker_id": "APR_002",
        },
        # Whitefield
        {
            "node_id": "NODE_WF_ROOFTOP_1",
            "building_id": "BLD_WHITEFIELD_TOWER",
            "node_name": "Whitefield Tower Rooftop",
            "latitude": 12.9716,
            "longitude": 77.6412,
            "altitude_msl": 955.0,
            "height_agl": 45.0,
            "node_type": "rooftop",
            "marker_id": "APR_003",
        },
        # Jayanagar
        {
            "node_id": "NODE_JN_ROOFTOP_1",
            "building_id": "BLD_JAYANAGAR_COMPLEX",
            "node_name": "Jayanagar Rooftop Service",
            "latitude": 12.9711,
            "longitude": 77.5532,
            "altitude_msl": 960.0,
            "height_agl": 30.0,
            "node_type": "rooftop",
            "marker_id": "APR_004",
        },
        # Indiranagar
        {
            "node_id": "NODE_IND_ROOFTOP_1",
            "building_id": "BLD_INDIRANAGAR_OFFICE",
            "node_name": "Indiranagar Business Park - Rooftop",
            "latitude": 12.9700,
            "longitude": 77.6400,
            "altitude_msl": 965.0,
            "height_agl": 50.0,
            "node_type": "rooftop",
            "marker_id": "APR_005",
        },
    ]
    
    for n_data in nodes_data:
        node = DeliveryNode(
            node_id=n_data["node_id"],
            building_id=n_data["building_id"],
            node_name=n_data["node_name"],
            location=f"POINTZ({n_data['longitude']} {n_data['latitude']} {n_data['altitude_msl']})",
            altitude_msl=n_data["altitude_msl"],
            height_agl=n_data["height_agl"],
            node_type=n_data["node_type"],
            marker_id=n_data["marker_id"],
            max_payload_kg=2.0,
        )
        db.add(node)
    
    db.commit()
    print("✅ Seeded 5 delivery nodes")


def seed_risk_voxels():
    """Seed initial risk voxels."""
    # Create a grid of risk voxels around buildings
    voxel_count = 0
    
    # High-risk zones around airports
    high_risk_zones = [
        {"lat": 13.2012, "lon": 77.7062, "risk": 0.8},  # Devanahalli
        {"lat": 12.9444, "lon": 77.6499, "risk": 0.7},  # HAL
    ]
    
    for zone in high_risk_zones:
        for alt in [950, 1000, 1050]:
            voxel = RiskVoxel(
                voxel_id=f"VOX_{uuid.uuid4().hex[:8].upper()}",
                center=f"POINTZ({zone['lon']} {zone['lat']} {alt})",
                composite_risk=zone["risk"],
                zone_color="red" if zone["risk"] > 0.7 else "yellow",
                flight_success_rate=0.7 if zone["risk"] > 0.7 else 0.85,
            )
            db.add(voxel)
            voxel_count += 1
    
    # Low-risk zones (green)
    for lat in [12.95, 13.00, 13.05]:
        for lon in [77.55, 77.60, 77.65]:
            voxel = RiskVoxel(
                voxel_id=f"VOX_{uuid.uuid4().hex[:8].upper()}",
                center=f"POINTZ({lon} {lat} 980)",
                composite_risk=0.15,
                zone_color="green",
                flight_success_rate=0.98,
            )
            db.add(voxel)
            voxel_count += 1
    
    db.commit()
    print(f"✅ Seeded {voxel_count} risk voxels")


def seed_obstacles():
    """Seed obstacle data."""
    obstacles_data = [
        {
            "obstacle_id": "OBS_COMM_TOWER_1",
            "name": "Communication Tower - Whitefield",
            "type": "antenna",
            "latitude": 12.9720,
            "longitude": 77.6400,
            "base_elev_msl": 910.0,
            "height_m": 80.0,
            "radius": 0.01,
        },
        {
            "obstacle_id": "OBS_POWER_LINE_1",
            "name": "High Voltage Power Line",
            "type": "power_line",
            "latitude": 12.9680,
            "longitude": 77.5950,
            "base_elev_msl": 920.0,
            "height_m": 15.0,
            "radius": 0.02,
        },
    ]
    
    for obs_data in obstacles_data:
        obstacle = Obstacle(
            obstacle_id=obs_data["obstacle_id"],
            obstacle_name=obs_data["name"],
            obstacle_type=obs_data["type"],
            base_location=f"POINT({obs_data['longitude']} {obs_data['latitude']})",
            base_elev_msl=obs_data["base_elev_msl"],
            top_elev_msl=obs_data["base_elev_msl"] + obs_data["height_m"],
            height_m=obs_data["height_m"],
            min_lat=obs_data["latitude"] - obs_data["radius"],
            max_lat=obs_data["latitude"] + obs_data["radius"],
            min_lon=obs_data["longitude"] - obs_data["radius"],
            max_lon=obs_data["longitude"] + obs_data["radius"],
        )
        db.add(obstacle)
    
    db.commit()
    print("✅ Seeded 2 obstacles")


def main():
    """Run all seed functions."""
    print("\n🌱 Starting database seeding...")
    
    try:
        # Clear existing data
        print("Clearing existing data...")
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
        
        # Seed data
        seed_buildings()
        seed_delivery_nodes()
        seed_risk_voxels()
        seed_obstacles()
        
        print("\n✅ Database seeding completed successfully!\n")
        
    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
