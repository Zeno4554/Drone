"""🚀 Quick Start Guide - Get Running in 5 Minutes."""

# 🚀 AeroCorridor - Quick Start (5 Minutes)

## Prerequisites
- Python 3.10+
- **Database (choose one):**
  - Option A: PostgreSQL + PostGIS installed locally
  - Option B: Supabase account (free tier available at https://supabase.com)
- (Optional: Railway.app & Streamlit Cloud accounts for deployment)

---

## 🗄️ Database Setup (Choose One Path)

### Path A: Local PostgreSQL (Recommended for Development)

Skip ahead to **Step 1: Terminal 1 - Backend Setup** below.

### Path B: Supabase (Recommended for Production)

1. **Create Supabase project** at https://supabase.com
2. **Get connection string** from Supabase dashboard
3. **Update `.env` file** with:
   ```env
   DATABASE_URL=postgresql://postgres:PASSWORD@PROJECT_ID.supabase.co:5432/postgres
   SUPABASE_MODE=true
   DB_POOL_SIZE=5
   ```
4. **Skip PostgreSQL setup steps** below
5. **Run seed_db.py** to populate Supabase
6. ✅ Ready to start backend!

📖 **Full Supabase setup guide**: See [docs/SUPABASE_SETUP.md](./docs/SUPABASE_SETUP.md)

---

## ⚡ Start Backend (Localhost)

### Step 1: Terminal 1 - Backend Setup
```bash
cd d:\Drone\backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
copy .env.example .env

# EDIT .env - Set your PostgreSQL credentials:
# DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/aerocorridor
```

### Step 2: Setup PostgreSQL Database
```bash
# In PowerShell as admin (or via pgAdmin)
createdb aerocorridor

# Run PostGIS initialization
psql -U postgres -d aerocorridor -f init.sql

# Seed test data
python seed_db.py
```

**✅ You should see:**
```
✅ Seeded 5 buildings
✅ Seeded 5 delivery nodes
✅ Seeded 20 risk voxels
✅ Seeded 2 obstacles
```

### Step 3: Start Backend Server
```bash
python run.py
```

**✅ Backend running at:** http://localhost:8000

View API docs: http://localhost:8000/docs

---

## ⚡ Start Frontend (Separate Terminal)

### Step 4: Terminal 2 - Frontend Setup
```bash
cd d:\Drone\frontend

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup secrets
copy .streamlit\secrets.toml.example .streamlit\secrets.toml

# secrets.toml should contain:
# API_URL = "http://localhost:8000"
```

### Step 5: Start Streamlit App
```bash
streamlit run app.py
```

**✅ Frontend running at:** http://localhost:8501

---

## 🎮 Test the System

### 1. Map Page (Building Selection)
- Go to: http://localhost:8501
- Click: **🗺️ Map** in sidebar
- Select a building from dropdown
- See delivery nodes with XYZ coordinates
- Click markers on interactive map

### 2. Orders Page (Place Delivery)
- Click: **📦 Orders** tab
- Click **Place Order** tab
- Select building → delivery node
- Set payload weight (0.1 - 2.5 kg)
- Click "📤 Place Order"
- ✅ Should show route plan with distance & risk score

### 3. Dashboard (Fleet Tracking)
- Click: **📊 Dashboard** 
- See 3 simulated drones on map
- Watch real-time altitude, speed, battery
- Click emergency controls: 🏠 RTH, ⬇️ Land

---

## 📊 Test Data Loaded

5 Buildings 🏢:
- Phoenix Mall
- Whitefield Tech Tower
- Jayanagar Complex
- Indiranagar Office
- KR Puram Retail

5 Delivery Nodes 📍:
- All with rooftop/dock access
- AprilTag marker IDs
- Altitude MSL coordinates
- Max 2kg payload capacity

3 Simulated Drones 🚁:
- DRONE_000 (active)
- DRONE_001 (idle)
- DRONE_002 (idle)

---

## 🔌 API Health Check

```bash
# Test backend connectivity
curl http://localhost:8000/health

# Should return:
# {"status": "healthy", "version": "2.0.0"}

# Get all buildings
curl http://localhost:8000/api/v1/buildings

# Get API documentation
curl http://localhost:8000/docs
```

---

## 🐛 Troubleshooting

### Backend won't start

**Error**: `Database connection refused`
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# If not running:
# Windows: Services → PostgreSQL → Start
# Mac: brew services start postgresql
# Linux: sudo systemctl start postgresql
```

**Error**: `ModuleNotFoundError: No module named 'geoalchemy2'`
```bash
pip install geoalchemy2==0.14.1
pip install psycopg2-binary==2.9.9
```

**Error**: `connection refused` after starting server
- Check `.env` DATABASE_URL is correct
- Verify database `aerocorridor` exists
- Run `python seed_db.py` again

### Frontend won't load

**Error**: `ConnectionError: Backend not responding`
```bash
# Verify backend is running
curl http://localhost:8000/health

# Check API_URL in frontend/.streamlit/secrets.toml
# Should be: API_URL = "http://localhost:8000"
```

**Error**: `ModuleNotFoundError: streamlit`
```bash
pip install -r requirements.txt
```

### Map not showing

- Clear Streamlit cache: `streamlit cache clear`
- Hard refresh browser: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
- Check browser console for errors (F12)

---

## 📂 Project Files Overview

```
d:\Drone
├── backend/              ← Start here (Python backend)
│   ├── app/
│   │   ├── models/      (8 database tables)
│   │   ├── routers/     (6 API endpoints)
│   │   └── services/    (route planner, telemetry, risk calc)
│   ├── requirements.txt
│   ├── run.py           (Start server: python run.py)
│   └── seed_db.py       (Load test data)
│
├── frontend/             ← Streamlit UI (Python)
│   ├── app.py           (Start app: streamlit run app.py)
│   ├── pages/           (3 pages: Map, Orders, Dashboard)
│   ├── components/      (Map rendering)
│   └── services/        (API client)
│
├── docs/
│   ├── BACKEND_SETUP.md    (Deep dive setup)
│   ├── FRONTEND_SETUP.md   (UI customization)
│   └── DEPLOYMENT.md       (Railway + Streamlit Cloud)
│
└── README.md            (Full documentation)
```

---

## 📋 Architecture at a Glance

```
Browser
  │
  ├─→ Streamlit UI (frontend/app.py)
  │        │
  │        └─→ HTTP/JSON
  │
  ├─→ FastAPI Backend (backend/app/main.py)
  │        │
  │        ├─→ Route Planner (A* algorithm)
  │        ├─→ Telemetry Simulator (3 drones)
  │        ├─→ Risk Calculator
  │        └─→ Database Access (SQLAlchemy)
  │
  └─→ PostgreSQL + PostGIS (GeospatialDB)
         └─→ 8 Tables (buildings, nodes, orders, etc.)
```

---

## ✅ Success Criteria

Your setup is working when:

1. ✅ Backend API docs load: http://localhost:8000/docs
2. ✅ Frontend loads: http://localhost:8501
3. ✅ "✅ Backend: Connected" appears in Streamlit sidebar
4. ✅ Map page shows 5 buildings
5. ✅ Can select a delivery node
6. ✅ Can place an order
7. ✅ Dashboard shows 3 drone positions
8. ✅ Emergency buttons (RTH, Land) are visible

---

## 🎯 What's Next

### Immediate (Testing)
1. Place a few test orders
2. Watch route planning work
3. Monitor telemetry updates
4. Test emergency controls

### Short-term (Customization)
1. Edit test buildings (docs/BACKEND_SETUP.md)
2. Add more delivery nodes
3. Customize map layers
4. Modify Streamlit theme

### Deployment (When Ready)
1. Deploy backend to Railway.app
2. Deploy frontend to Streamlit Cloud
3. Update API_URL in frontend secrets
4. See live demo: https://your-app.streamlit.app

---

## 🔗 Useful Links

- **Backend Docs**: http://localhost:8000/docs (Swagger UI)
- **Backend API Root**: http://localhost:8000/api/v1
- **Frontend**: http://localhost:8501
- **PostgreSQL**: localhost:5432

---

## 📞 Help & Docs

- Quick Start: THIS FILE ← YOU ARE HERE
- Full README: [README.md](README.md)
- Backend Guide: [docs/BACKEND_SETUP.md](docs/BACKEND_SETUP.md)
- Frontend Guide: [docs/FRONTEND_SETUP.md](docs/FRONTEND_SETUP.md)
- Deployment: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## 🎉 You're Ready!

**Total setup time: ~5 minutes**

Backend + Frontend + Database all running locally ✅

**Next**: Visit http://localhost:8501 and start exploring!

---

*Questions? Check the relevant guide above or review source code - everything is well-documented.*

*🎯 Ready for April 17 Expo Demo!*
