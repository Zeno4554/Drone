"""Project root README."""

# 🚁 AeroCorridor - 3D Drone Delivery Navigation System

A complete Python full-stack application for autonomous drone delivery with real-time tracking, 3D route planning, and operator controls.

## ✨ Features

- **3D Route Planning**: A* pathfinding with MSL-normalized altitude system
- **Real-time Telemetry**: WebSocket-based live drone tracking
- **Risk Assessment**: 5-tier risk zone visualization (Green/Grey/Yellow/Red/Black)
- **Operator Dashboard**: Fleet management, emergency controls, flight history
- **Building Integration**: Delivery nodes on rooftops, balconies, docks with AprilTag landing markers
- **PostGIS Spatial Queries**: Efficient geographic lookups and proximity searches

## 🏗️ Project Structure

```
AeroCorridor/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI application
│   │   ├── config.py          # Configuration
│   │   ├── database.py        # Database setup
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── routers/           # API routes
│   │   └── services/          # Business logic (route planner, telemetry sim)
│   ├── requirements.txt        # Python dependencies
│   ├── seed_db.py             # Database seeding script
│   ├── init.sql               # PostgreSQL + PostGIS initialization
│   └── run.py                 # Development server launcher
│
├── frontend/                   # Streamlit web UI
│   ├── app.py                 # Main Streamlit app
│   ├── pages/                 # Multi-page app pages
│   ├── components/            # Reusable Streamlit components
│   ├── services/              # API client, utilities
│   ├── requirements.txt        # Python dependencies
│   ├── .streamlit/            # Streamlit configuration
│   └── .streamlit/secrets.toml # API secrets (not in repo)
│
├── config/                     # Shared configuration
├── docs/                       # Documentation
└── .gitignore
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- **Database (Choose one):**
  - Option A: PostgreSQL 14+ with PostGIS extension (local development)
  - Option B: Supabase account (free tier - managed PostgreSQL with PostGIS)
- Railway.app account (for backend deployment)
- Streamlit Cloud account (for frontend deployment)

### 🗄️ Database Setup

**Choose your database approach:**

**Option A: Local PostgreSQL** (Development - Recommended)
```bash
postgres=# CREATE DATABASE aerocorridor;
postgres=# CREATE EXTENSION postgis;
```

**Option B: Supabase** (Production - Managed Service)
1. Create free account at https://supabase.com
2. Create project and get connection string
3. PostGIS is automatically available

📖 **See [docs/SUPABASE_SETUP.md](./docs/SUPABASE_SETUP.md) for detailed Supabase setup**

### Local Development

#### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your PostgreSQL connection string

# Initialize database with test data
python seed_db.py

# Run development server
python run.py
```

Backend will be available at: http://localhost:8000

API docs: http://localhost:8000/docs

#### 2. Frontend Setup

```bash
cd frontend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create secrets file
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit to set API_URL=http://localhost:8000

# Run Streamlit app
streamlit run app.py
```

Frontend will be available at: http://localhost:8501

## 📡 API Endpoints

### Buildings
- `GET /api/v1/buildings` - List all buildings
- `GET /api/v1/buildings/{id}` - Get building details
- `POST /api/v1/buildings` - Create building

### Delivery Nodes
- `GET /api/v1/nodes` - List all nodes
- `GET /api/v1/nodes/building/{id}` - Get nodes for building
- `GET /api/v1/nodes/{id}` - Get node details
- `POST /api/v1/nodes` - Create node

### Orders
- `GET /api/v1/orders` - List orders
- `POST /api/v1/orders` - Place order
- `PATCH /api/v1/orders/{id}` - Update order
- `POST /api/v1/orders/{id}/assign-route` - Assign route to order

### Route Planning
- `POST /api/v1/routes` - Plan 3D route (A* pathfinding)
- `POST /api/v1/routes/validate` - Validate proposed route
- `GET /api/v1/routes/suggestions/{node_id}` - Get route alternatives

### Map Data (GeoJSON)
- `GET /api/v1/map/buildings/geojson` - Buildings as GeoJSON
- `GET /api/v1/map/nodes/geojson` - Delivery nodes as GeoJSON
- `GET /api/v1/map/risk-zones/geojson` - Risk voxels as GeoJSON
- `POST /api/v1/map/risk-heatmap` - Generate 3D risk heatmap

### Telemetry & Tracking
- `GET /api/v1/telemetry/current` - Current telemetry all drones
- `GET /api/v1/telemetry/drone/{id}` - Single drone telemetry
- `WS /api/v1/telemetry/ws` - WebSocket real-time telemetry stream
- `POST /api/v1/telemetry/drone/{id}/emergency-rth` - Emergency Return-to-Home
- `POST /api/v1/telemetry/drone/{id}/land` - Land drone

## 🎮 Streamlit Pages

1. **🗺️ Map** - Building selection, delivery node picker, route visualization
2. **📦 Orders** - Place orders, track deliveries, order history
3. **📊 Dashboard** - Fleet monitoring, live telemetry, emergency controls

## 🗄️ Database Schema

8 Core Tables:
- `buildings` - Building data with PostGIS location
- `delivery_nodes` - Rooftops, balconies, docks with 3D coordinates
- `orders` - Order records with route assignments
- `risk_voxels` - 3D risk grid (5m × 5m × 5m voxels)
- `obstacles` - Buildings, trees, power lines, antenna towers
- `flight_logs` - Completed flight records
- `telemetry` - Real-time drone position, heading, battery
- `users` - Operator accounts and access control

PostGIS indexes for O(log N) spatial queries.

## 🔧 Route Planning Algorithm

**A* Pathfinding on 3D Voxel Grid**

- Voxel size: 5m × 5m × 5m
- Heuristic: Euclidean distance to goal
- Cost function: distance + risk score + altitude change
- Altitude constraints: 100-200m AGL (980-1040m MSL for Bengaluru)
- Obstacle avoidance: Building AABB collision detection
- Risk weighting: 40% obstacles, 20% altitude, 20% air traffic, 20% wind

## 📊 Test Data

Pre-seeded with Bengaluru demo data:
- 5 buildings (Phoenix Mall, Whitefield, Jayanagar, Indiranagar, KR Puram)
- 5 delivery nodes with AprilTag markers
- Risk zones around Devanahalli & HAL airports
- Obstacles: Communication towers, power lines

## 🌐 Deployment

### Backend (Railway.app)

```bash
cd backend

# Initialize Railway project
railway init

# Select: New Project → PostgreSQL → Dockerfile

# Deploy
railway up

# Set environment variables in Railway dashboard
# DATABASE_URL, CORS_ORIGINS, etc.
```

### Frontend (Streamlit Cloud)

1. Push code to GitHub
2. Go to streamlit.io/cloud
3. Connect repository
4. Select `frontend` as root directory
5. Set secrets:
   ```
   API_URL = "https://your-railway-backend.railway.app"
   ```
6. Deploy (auto-deploys on git push)

## 📈 Performance Notes

- Spatial indexes (GIST) on location columns
- Connection pooling: 10 base + 20 overflow
- Telemetry WebSocket: 500ms update interval
- Voxel grid: 26-neighbor topology (6 cardinal + 12 diagonal + 8 corner)
- A* optimized with binary heap priority queue

## 🧪 Testing

```bash
# Backend tests (pytest)
cd backend
pytest tests/

# Frontend tests (pytest + streamlit)
cd frontend
pytest tests/
```

## 📝 Logs

- Backend: `backend/logs/` (structured JSON logging)
- Telemetry: Real-time WebSocket stream (500ms)
- Flight records: Stored in PostgreSQL `flight_logs` table

## 🎯 Roadmap

- [x] Phase 1: Database schema + CRUD APIs
- [x] Phase 2: Route planner + Streamlit UI (THIS)
- [ ] Phase 3: Risk intelligence, emergency controls
- [ ] Phase 4: Deployment, stress testing
- [ ] Phase 5: Multi-drone coordination
- [ ] Phase 6: ML-based collision avoidance

## 📞 Support

For issues or questions: GitHub Issues

## 📄 License

[Your License Here]

---

**🎯 Demoing at International Drone Expo 2026 - April 17**
