"""Idempotent demo data bootstrap — 10 Indian cities nationwide."""

import uuid
from sqlalchemy.orm import Session

from ..models.building import Building
from ..models.delivery_node import DeliveryNode
from ..models.risk_voxel import RiskVoxel
from ..models.obstacle import Obstacle

# ── 10 cities, 2 buildings each ──────────────────────────────────────────────

BUILDINGS = [
    # Delhi
    {"building_id": "BLD_DEL_CONNAUGHT", "name": "Connaught Place Tower", "city": "Delhi",
     "lat": 28.6315, "lon": 77.2167, "ground_elev_msl": 216.0, "height_m": 40.0},
    {"building_id": "BLD_DEL_CYBERHUB", "name": "DLF CyberHub", "city": "Delhi",
     "lat": 28.4949, "lon": 77.0886, "ground_elev_msl": 218.0, "height_m": 55.0},
    # Mumbai
    {"building_id": "BLD_MUM_BKC", "name": "BKC Trade Tower", "city": "Mumbai",
     "lat": 19.0658, "lon": 72.8699, "ground_elev_msl": 14.0, "height_m": 60.0},
    {"building_id": "BLD_MUM_ANDHERI", "name": "Andheri Logistics Hub", "city": "Mumbai",
     "lat": 19.1197, "lon": 72.8464, "ground_elev_msl": 12.0, "height_m": 30.0},
    # Bengaluru
    {"building_id": "BLD_BLR_PHOENIX", "name": "Phoenix Mall", "city": "Bengaluru",
     "lat": 12.9716, "lon": 77.5946, "ground_elev_msl": 920.0, "height_m": 35.0},
    {"building_id": "BLD_BLR_WHITEFIELD", "name": "Whitefield Tech Tower", "city": "Bengaluru",
     "lat": 12.9698, "lon": 77.7500, "ground_elev_msl": 910.0, "height_m": 45.0},
    # Chennai
    {"building_id": "BLD_CHN_TIDEL", "name": "Tidel Park", "city": "Chennai",
     "lat": 12.9889, "lon": 80.2467, "ground_elev_msl": 6.0, "height_m": 50.0},
    {"building_id": "BLD_CHN_EXPRESS", "name": "Express Avenue Mall", "city": "Chennai",
     "lat": 13.0582, "lon": 80.2634, "ground_elev_msl": 8.0, "height_m": 35.0},
    # Hyderabad
    {"building_id": "BLD_HYD_HITEC", "name": "HITEC City Tower", "city": "Hyderabad",
     "lat": 17.4435, "lon": 78.3772, "ground_elev_msl": 542.0, "height_m": 55.0},
    {"building_id": "BLD_HYD_GACHIBOWLI", "name": "Gachibowli IT Park", "city": "Hyderabad",
     "lat": 17.4401, "lon": 78.3489, "ground_elev_msl": 545.0, "height_m": 40.0},
    # Kolkata
    {"building_id": "BLD_KOL_SALTLAKE", "name": "Salt Lake Sector V Hub", "city": "Kolkata",
     "lat": 22.5726, "lon": 88.4312, "ground_elev_msl": 9.0, "height_m": 45.0},
    {"building_id": "BLD_KOL_PARKSTREET", "name": "Park Street Centre", "city": "Kolkata",
     "lat": 22.5507, "lon": 88.3532, "ground_elev_msl": 11.0, "height_m": 30.0},
    # Pune
    {"building_id": "BLD_PUN_HINJEWADI", "name": "Hinjewadi IT Park", "city": "Pune",
     "lat": 18.5912, "lon": 73.7390, "ground_elev_msl": 560.0, "height_m": 50.0},
    {"building_id": "BLD_PUN_KOREGAON", "name": "Koregaon Park Tower", "city": "Pune",
     "lat": 18.5362, "lon": 73.8939, "ground_elev_msl": 565.0, "height_m": 35.0},
    # Ahmedabad
    {"building_id": "BLD_AMD_GIFT", "name": "GIFT City Tower", "city": "Ahmedabad",
     "lat": 23.1171, "lon": 72.5714, "ground_elev_msl": 53.0, "height_m": 60.0},
    {"building_id": "BLD_AMD_SGROAD", "name": "SG Highway Complex", "city": "Ahmedabad",
     "lat": 23.0300, "lon": 72.5077, "ground_elev_msl": 55.0, "height_m": 30.0},
    # Jaipur
    {"building_id": "BLD_JAI_MANSAROVAR", "name": "Mansarovar Business Park", "city": "Jaipur",
     "lat": 26.8550, "lon": 75.7633, "ground_elev_msl": 431.0, "height_m": 35.0},
    {"building_id": "BLD_JAI_MALVIYA", "name": "Malviya Nagar Centre", "city": "Jaipur",
     "lat": 26.8481, "lon": 75.8150, "ground_elev_msl": 434.0, "height_m": 28.0},
    # Lucknow
    {"building_id": "BLD_LKO_GOMTI", "name": "Gomti Nagar Hub", "city": "Lucknow",
     "lat": 26.8501, "lon": 80.9914, "ground_elev_msl": 123.0, "height_m": 40.0},
    {"building_id": "BLD_LKO_HAZRATGANJ", "name": "Hazratganj Complex", "city": "Lucknow",
     "lat": 26.8505, "lon": 80.9459, "ground_elev_msl": 125.0, "height_m": 30.0},
]

# One rooftop node per building
NODES = [
    {"node_id": "NODE_DEL_CP_R1", "building_id": "BLD_DEL_CONNAUGHT",
     "node_name": "Connaught Place Rooftop", "lat": 28.6315, "lon": 77.2167,
     "altitude_msl": 256.0, "height_agl": 40.0, "node_type": "rooftop", "marker_id": "APR_D01"},
    {"node_id": "NODE_DEL_CH_R1", "building_id": "BLD_DEL_CYBERHUB",
     "node_name": "CyberHub Rooftop", "lat": 28.4949, "lon": 77.0886,
     "altitude_msl": 273.0, "height_agl": 55.0, "node_type": "rooftop", "marker_id": "APR_D02"},
    {"node_id": "NODE_MUM_BKC_R1", "building_id": "BLD_MUM_BKC",
     "node_name": "BKC Trade Rooftop", "lat": 19.0658, "lon": 72.8699,
     "altitude_msl": 74.0, "height_agl": 60.0, "node_type": "rooftop", "marker_id": "APR_M01"},
    {"node_id": "NODE_MUM_AND_R1", "building_id": "BLD_MUM_ANDHERI",
     "node_name": "Andheri Hub Dock", "lat": 19.1197, "lon": 72.8464,
     "altitude_msl": 42.0, "height_agl": 30.0, "node_type": "dock", "marker_id": "APR_M02"},
    {"node_id": "NODE_BLR_PHX_R1", "building_id": "BLD_BLR_PHOENIX",
     "node_name": "Phoenix Mall Rooftop", "lat": 12.9716, "lon": 77.5946,
     "altitude_msl": 955.0, "height_agl": 35.0, "node_type": "rooftop", "marker_id": "APR_B01"},
    {"node_id": "NODE_BLR_WF_R1", "building_id": "BLD_BLR_WHITEFIELD",
     "node_name": "Whitefield Tower Rooftop", "lat": 12.9698, "lon": 77.7500,
     "altitude_msl": 955.0, "height_agl": 45.0, "node_type": "rooftop", "marker_id": "APR_B02"},
    {"node_id": "NODE_CHN_TID_R1", "building_id": "BLD_CHN_TIDEL",
     "node_name": "Tidel Park Rooftop", "lat": 12.9889, "lon": 80.2467,
     "altitude_msl": 56.0, "height_agl": 50.0, "node_type": "rooftop", "marker_id": "APR_C01"},
    {"node_id": "NODE_CHN_EXP_R1", "building_id": "BLD_CHN_EXPRESS",
     "node_name": "Express Avenue Rooftop", "lat": 13.0582, "lon": 80.2634,
     "altitude_msl": 43.0, "height_agl": 35.0, "node_type": "rooftop", "marker_id": "APR_C02"},
    {"node_id": "NODE_HYD_HIT_R1", "building_id": "BLD_HYD_HITEC",
     "node_name": "HITEC City Rooftop", "lat": 17.4435, "lon": 78.3772,
     "altitude_msl": 597.0, "height_agl": 55.0, "node_type": "rooftop", "marker_id": "APR_H01"},
    {"node_id": "NODE_HYD_GAC_R1", "building_id": "BLD_HYD_GACHIBOWLI",
     "node_name": "Gachibowli Dock", "lat": 17.4401, "lon": 78.3489,
     "altitude_msl": 585.0, "height_agl": 40.0, "node_type": "dock", "marker_id": "APR_H02"},
    {"node_id": "NODE_KOL_SL_R1", "building_id": "BLD_KOL_SALTLAKE",
     "node_name": "Salt Lake Rooftop", "lat": 22.5726, "lon": 88.4312,
     "altitude_msl": 54.0, "height_agl": 45.0, "node_type": "rooftop", "marker_id": "APR_K01"},
    {"node_id": "NODE_KOL_PS_R1", "building_id": "BLD_KOL_PARKSTREET",
     "node_name": "Park Street Dock", "lat": 22.5507, "lon": 88.3532,
     "altitude_msl": 41.0, "height_agl": 30.0, "node_type": "dock", "marker_id": "APR_K02"},
    {"node_id": "NODE_PUN_HIN_R1", "building_id": "BLD_PUN_HINJEWADI",
     "node_name": "Hinjewadi Rooftop", "lat": 18.5912, "lon": 73.7390,
     "altitude_msl": 610.0, "height_agl": 50.0, "node_type": "rooftop", "marker_id": "APR_P01"},
    {"node_id": "NODE_PUN_KP_R1", "building_id": "BLD_PUN_KOREGAON",
     "node_name": "Koregaon Park Dock", "lat": 18.5362, "lon": 73.8939,
     "altitude_msl": 600.0, "height_agl": 35.0, "node_type": "dock", "marker_id": "APR_P02"},
    {"node_id": "NODE_AMD_GIFT_R1", "building_id": "BLD_AMD_GIFT",
     "node_name": "GIFT City Rooftop", "lat": 23.1171, "lon": 72.5714,
     "altitude_msl": 113.0, "height_agl": 60.0, "node_type": "rooftop", "marker_id": "APR_A01"},
    {"node_id": "NODE_AMD_SG_R1", "building_id": "BLD_AMD_SGROAD",
     "node_name": "SG Highway Dock", "lat": 23.0300, "lon": 72.5077,
     "altitude_msl": 85.0, "height_agl": 30.0, "node_type": "dock", "marker_id": "APR_A02"},
    {"node_id": "NODE_JAI_MAN_R1", "building_id": "BLD_JAI_MANSAROVAR",
     "node_name": "Mansarovar Rooftop", "lat": 26.8550, "lon": 75.7633,
     "altitude_msl": 466.0, "height_agl": 35.0, "node_type": "rooftop", "marker_id": "APR_J01"},
    {"node_id": "NODE_JAI_MAL_R1", "building_id": "BLD_JAI_MALVIYA",
     "node_name": "Malviya Nagar Dock", "lat": 26.8481, "lon": 75.8150,
     "altitude_msl": 462.0, "height_agl": 28.0, "node_type": "dock", "marker_id": "APR_J02"},
    {"node_id": "NODE_LKO_GN_R1", "building_id": "BLD_LKO_GOMTI",
     "node_name": "Gomti Nagar Rooftop", "lat": 26.8501, "lon": 80.9914,
     "altitude_msl": 163.0, "height_agl": 40.0, "node_type": "rooftop", "marker_id": "APR_L01"},
    {"node_id": "NODE_LKO_HG_R1", "building_id": "BLD_LKO_HAZRATGANJ",
     "node_name": "Hazratganj Dock", "lat": 26.8505, "lon": 80.9459,
     "altitude_msl": 155.0, "height_agl": 30.0, "node_type": "dock", "marker_id": "APR_L02"},
]

# High-risk zones near major airports
HIGH_RISK_ZONES = [
    {"lat": 28.5562, "lon": 77.1000, "risk": 0.85},   # IGI Airport, Delhi
    {"lat": 19.0896, "lon": 72.8656, "risk": 0.80},   # CSIA, Mumbai
    {"lat": 12.9941, "lon": 80.1709, "risk": 0.75},   # Chennai Airport
    {"lat": 17.2403, "lon": 78.4294, "risk": 0.78},   # RGIA, Hyderabad
    {"lat": 22.6520, "lon": 88.4463, "risk": 0.72},   # NSCBI, Kolkata
    {"lat": 13.1989, "lon": 77.7068, "risk": 0.80},   # Kempegowda, Bengaluru
]

# Low-risk green zones (spread across cities)
LOW_RISK_COORDS = [
    (28.63, 77.22), (19.07, 72.88), (12.97, 77.60),
    (13.06, 80.27), (17.44, 78.38), (22.57, 88.43),
    (18.55, 73.85), (23.03, 72.57), (26.85, 75.78),
    (26.85, 80.95),
]

OBSTACLES = [
    {"obstacle_id": "OBS_DEL_TOWER_1", "name": "Delhi Comm Tower",
     "type": "antenna", "lat": 28.6200, "lon": 77.2100,
     "base_elev_msl": 216.0, "height_m": 90.0, "radius": 0.01},
    {"obstacle_id": "OBS_MUM_POWER_1", "name": "Mumbai HV Power Line",
     "type": "power_line", "lat": 19.1000, "lon": 72.8600,
     "base_elev_msl": 14.0, "height_m": 20.0, "radius": 0.02},
    {"obstacle_id": "OBS_BLR_TOWER_1", "name": "Bengaluru Comm Tower",
     "type": "antenna", "lat": 12.9720, "lon": 77.6400,
     "base_elev_msl": 910.0, "height_m": 80.0, "radius": 0.01},
    {"obstacle_id": "OBS_HYD_TOWER_1", "name": "Hyderabad Comm Tower",
     "type": "antenna", "lat": 17.4500, "lon": 78.3800,
     "base_elev_msl": 542.0, "height_m": 70.0, "radius": 0.01},
]


def ensure_demo_data(db: Session) -> dict:
    """Insert demo data only if the DB is empty. Returns counts."""
    counts = {"buildings": 0, "nodes": 0, "risk_voxels": 0, "obstacles": 0, "skipped": False}

    if db.query(Building).count() > 0:
        counts["skipped"] = True
        return counts

    for b in BUILDINGS:
        db.add(Building(
            building_id=b["building_id"], name=b["name"], city=b["city"],
            location=f"POINT({b['lon']} {b['lat']})",
            ground_elev_msl=b["ground_elev_msl"], height_m=b["height_m"],
            top_elev_msl=b["ground_elev_msl"] + b["height_m"],
        ))
        counts["buildings"] += 1

    for n in NODES:
        db.add(DeliveryNode(
            node_id=n["node_id"], building_id=n["building_id"],
            node_name=n["node_name"],
            location=f"POINTZ({n['lon']} {n['lat']} {n['altitude_msl']})",
            altitude_msl=n["altitude_msl"], height_agl=n["height_agl"],
            node_type=n["node_type"], marker_id=n["marker_id"],
            max_payload_kg=2.5,
        ))
        counts["nodes"] += 1

    for zone in HIGH_RISK_ZONES:
        for alt_offset in [0, 50, 100]:
            base_alt = 300 + alt_offset
            db.add(RiskVoxel(
                voxel_id=f"VOX_{uuid.uuid4().hex[:8].upper()}",
                center=f"POINTZ({zone['lon']} {zone['lat']} {base_alt})",
                composite_risk=zone["risk"],
                zone_color="red" if zone["risk"] > 0.75 else "yellow",
                flight_success_rate=0.65 if zone["risk"] > 0.75 else 0.80,
            ))
            counts["risk_voxels"] += 1

    for lat, lon in LOW_RISK_COORDS:
        db.add(RiskVoxel(
            voxel_id=f"VOX_{uuid.uuid4().hex[:8].upper()}",
            center=f"POINTZ({lon} {lat} 300)",
            composite_risk=0.12, zone_color="green", flight_success_rate=0.98,
        ))
        counts["risk_voxels"] += 1

    for obs in OBSTACLES:
        db.add(Obstacle(
            obstacle_id=obs["obstacle_id"],
            obstacle_name=obs["name"], obstacle_type=obs["type"],
            base_location=f"POINT({obs['lon']} {obs['lat']})",
            base_elev_msl=obs["base_elev_msl"],
            top_elev_msl=obs["base_elev_msl"] + obs["height_m"],
            height_m=obs["height_m"],
            min_lat=obs["lat"] - obs["radius"], max_lat=obs["lat"] + obs["radius"],
            min_lon=obs["lon"] - obs["radius"], max_lon=obs["lon"] + obs["radius"],
        ))
        counts["obstacles"] += 1

    db.commit()
    return counts


def reseed_demo_data(db: Session) -> dict:
    """Clear all data and re-seed. Use for switching from old Bengaluru-only data."""
    from ..models import Base
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    return ensure_demo_data(db)
