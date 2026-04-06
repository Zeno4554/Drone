"""Backend setup and installation guide."""

# Backend Setup Guide

## Prerequisites

1. **Python 3.10+**
   ```bash
   python --version  # Should show 3.10 or higher
   ```

2. **PostgreSQL 14+**
   - Download: https://www.postgresql.org/download/
   - With PostGIS extension: `CREATE EXTENSION postgis;`

3. **Git** (optional, for version control)

## Installation

### 1. Clone/Extract Project

```bash
cd d:\Drone
```

### 2. Create Virtual Environment

```bash
cd backend

# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables

```bash
# Copy example to .env
copy .env.example .env

# Edit .env with your database credentials
# DATABASE_URL=postgresql://postgres:your_password@localhost:5432/aerocorridor
```


```

### 6. Seed Test Data

```bash
python seed_db.py
```

You should see:
```
✅ Seeded 5 buildings
✅ Seeded 5 delivery nodes
✅ Seeded 20 risk voxels
✅ Seeded 2 obstacles
```

### 7. Run Development Server

```bash
python run.py
```

Server starts at: **http://localhost:8000**

### 8. Verify Installation

Visit in browser:
- API Root: http://localhost:8000/api/v1
- API Docs (Swagger): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## Project Layout

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Settings
│   ├── database.py             # DB connection
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── building.py
│   │   ├── delivery_node.py
│   │   ├── order.py
│   │   ├── risk_voxel.py
│   │   ├── obstacle.py
│   │   ├── flight_log.py
│   │   ├── telemetry.py
│   │   └── user.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── buildings.py
│   │   ├── delivery_nodes.py
│   │   ├── orders.py
│   │   ├── routes.py
│   │   ├── map.py
│   │   └── telemetry.py
│   └── services/
│       ├── route_planner.py
│       ├── risk_calculator.py
│       └── telemetry_simulator.py
├── requirements.txt
├── .env.example
├── run.py
├── seed_db.py
└── init.sql
```

## Environment Variables

```
DATABASE_URL=postgresql://user:password@localhost:5432/aerocorridor
CORS_ORIGINS=["*"]
API_V1_PREFIX=/api/v1
PROJECT_NAME=AeroCorridor
VERSION=2.0.0
VOXEL_SIZE_M=5.0
CRUISE_ALTITUDE_AGL_M=100.0
MAX_ALTITUDE_AGL_M=200.0
TELEMETRY_UPDATE_INTERVAL_MS=500
DRONE_COUNT=3
BENGALURU_GROUND_ELEV_MSL=920.0
ENABLE_TELEMETRY_SIMULATION=true
```

## Database Connection Issues

If you get connection errors:

### 1. Check PostgreSQL is running
```bash
# Windows
pg_isready -h localhost -p 5432

# macOS/Linux
brew services list  # or: systemctl status postgresql
```

### 2. Verify credentials
```bash
psql -U postgres -d aerocorridor
```

### 3. Check .env file
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/aerocorridor
```

Replace `YOUR_PASSWORD` with your PostgreSQL password.

### 4. Reset database
```bash
# Drop and recreate
dropdb aerocorridor
createdb aerocorridor
psql -U postgres -d aerocorridor -f init.sql
python seed_db.py
```

## Common Issues

### ImportError: No module named 'geoalchemy2'
```bash
pip install geoalchemy2==0.14.1
```

### ImportError: No module named 'psycopg2'
```bash
pip install psycopg2-binary==2.9.9
```

### psycopg2.OperationalError: could not connect to server
- PostgreSQL not running
- Wrong credentials in .env
- Database doesn't exist

### 'CREATE EXTENSION postgis' errors
- PostGIS not installed on system
- On Windows: Download PostgreSQL with PostGIS included
- On Mac: `brew install postgis`
- On Linux: `sudo apt install postgis postgresql-14-postgis-3`

## Running Tests

```bash
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_routes.py
```

## API Testing with cURL

```bash
# List buildings
curl http://localhost:8000/api/v1/buildings

# Get API docs
curl http://localhost:8000/docs

# Plan a route
curl -X POST http://localhost:8000/api/v1/routes \
  -H "Content-Type: application/json" \
  -d '{"source_lat": 12.9716, "source_lon": 77.5946, "source_alt_msl": 980.0, "destination_node_id": "NODE_PHX_ROOFTOP_1"}'
```

## Next Steps

1. ✅ Backend running on http://localhost:8000
2. ⭐ Setup frontend in ../frontend/ folder
3. 🚀 Deploy to Railway.app when ready

## Troubleshooting

### Check Status
```bash
python run.py
```

Look for:
```
✅ Database initialized
🚀 Starting AeroCorridor Backend
```

### View Logs
```bash
# View last 50 lines
tail -50 backend.log
```

### Reset Everything
```bash
python seed_db.py  # Re-seed data
```

## Deployment Preparation

Before deploying to Railway:

1. Set `DEBUG=false` in production
2. Update `CORS_ORIGINS` with actual frontend domain
3. Use strong PostgreSQL credentials
4. Enable SSL for database connection
5. Setup environment variables in Railway dashboard

---

Need help? Check: http://localhost:8000/docs (interactive API documentation)
