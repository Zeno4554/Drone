"""Supabase Setup Guide for AeroCorridor Backend."""

# 🚀 Supabase Setup Guide

AeroCorridor backend is now configured to work with both **local PostgreSQL** and **Supabase**.

---

## 🎯 What is Supabase?

Supabase is a **managed PostgreSQL database service** with:
- ✅ Built-in PostGIS for spatial queries
- ✅ Automatic SSL/TLS connection
- ✅ Real-time database features
- ✅ Auto-scaling
- ✅ Automatic backups
- ✅ Free tier available: https://supabase.com

---

## 📋 Prerequisites

1. **Supabase Account** - Sign up free at https://supabase.com
2. **Supabase Project** - Create a new project
3. **Backend configured** - Already prepared with Supabase support

---

## 🔧 Setup Steps

### Step 1: Create Supabase Project

1. Go to https://supabase.com and sign up (free)
2. Click **"New Project"**
3. Enter:
   - **Name**: aerocorridor
   - **Database Password**: (save somewhere safe!)
   - **Region**: Closest to your location
4. Click **Create new project**
5. Wait for project to initialize (~2 mins)

### Step 2: Get Supabase Connection String

1. In Supabase dashboard, click **Settings** (⚙️ icon)
2. Select **Database** from left menu
3. Find **Connection string** section
4. Click on **URI** tab
5. Copy the connection string (looks like):
   ```
   postgresql://postgres:YOUR_PASSWORD@YOUR_PROJECT_ID.supabase.co:5432/postgres
   ```

**Replace placeholders:**
- `YOUR_PASSWORD`: The database password you set
- `YOUR_PROJECT_ID`: Found in your project URL

### Step 3: Update Backend .env

In `backend/.env`:

```env
# Supabase Configuration
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_PROJECT_ID.supabase.co:5432/postgres
SUPABASE_MODE=true
DB_POOL_SIZE=5

# Rest of configuration remains the same...
CORS_ORIGINS=["*"]
API_V1_PREFIX=/api/v1
# ... etc
```

**Important**: 
- Set `SUPABASE_MODE=true` to enable SSL
- Use smaller `DB_POOL_SIZE=5` (Supabase recommends this)

### Step 4: Enable PostGIS Extension

Supabase comes with PostGIS, but verify it's enabled:

1. In Supabase dashboard, go to **SQL Editor**
2. Click **New Query**
3. Run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   CREATE EXTENSION IF NOT EXISTS postgis_topology;
   ```
4. Click **Run**

✅ PostGIS is now enabled

### Step 5: Create Spatial Indexes

Run the initialization script in SQL Editor:

```sql
-- Create indexes for spatial queries
CREATE INDEX IF NOT EXISTS idx_buildings_location ON buildings USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_delivery_nodes_location ON delivery_nodes USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_obstacles_base_loc ON obstacles USING GIST(base_location);
CREATE INDEX IF NOT EXISTS idx_risk_voxel_center ON risk_voxels USING GIST(center);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_buildings_city ON buildings(city);
CREATE INDEX IF NOT EXISTS idx_nodes_building_id ON delivery_nodes(building_id);
CREATE INDEX IF NOT EXISTS idx_orders_destination ON orders(destination_node_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_drone_id ON telemetry(drone_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_created_at ON telemetry(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_flight_logs_drone_id ON flight_logs(drone_id);
CREATE INDEX IF NOT EXISTS idx_risk_zone_color ON risk_voxels(zone_color);

-- Create helpful functions
CREATE OR REPLACE FUNCTION nearby_buildings(lat FLOAT, lon FLOAT, radius_km FLOAT DEFAULT 1.0)
RETURNS TABLE(building_id VARCHAR, name TEXT, distance_km FLOAT) AS $$
  SELECT 
    b.building_id,
    b.name,
    ST_DistanceSphere(b.location, ST_Point(lon, lat)) / 1000.0 as distance_km
  FROM buildings b
  WHERE ST_DWithin(b.location, ST_Point(lon, lat), radius_km * 1000)
  ORDER BY distance_km;
$$ LANGUAGE SQL;

VACUUM ANALYZE;
```

### Step 6: Seed Test Data

```bash
cd backend

# Activate virtual environment
venv\Scripts\activate

# Run seeding script
python seed_db.py
```

**Output should show:**
```
🔒 Connecting to Supabase...
✅ Seeded 5 buildings
✅ Seeded 5 delivery nodes
✅ Seeded 20+ risk voxels
✅ Seeded 2 obstacles
```

### Step 7: Start Backend

```bash
python run.py
```

Expected output:
```
🚀 Starting AeroCorridor Backend
Database: postgresql://postgres:***@xxx.supabase.co:5432/postgres
API URL: http://localhost:8000/api/v1
✅ Database initialized
```

---

## ✅ Verification

### Test Connection

```bash
curl http://localhost:8000/health
```

Should return:
```json
{"status": "healthy", "version": "2.0.0"}
```

### Test API

```bash
curl http://localhost:8000/api/v1/buildings
```

Should return your buildings (if seeded).

### View in Supabase Dashboard

1. Go to **Supabase Dashboard**
2. Click **SQL Editor**
3. Run:
   ```sql
   SELECT * FROM buildings;
   SELECT * FROM delivery_nodes;
   SELECT COUNT(*) FROM orders;
   ```

---

## 🔒 Security Best Practices

### 1. Protect Your Connection String

✅ **DO:**
- Store in `.env` file (git-ignored)
- Use environment variables in production
- Rotate password quarterly

❌ **DON'T:**
- Commit `.env` to Git
- Share password via chat/email
- Use weak passwords

### 2. Set Row-Level Security (RLS)

In Supabase SQL Editor, restrict access:

```sql
ALTER TABLE buildings ENABLE ROW LEVEL SECURITY;
ALTER TABLE delivery_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
-- ... for all tables

-- Allow public read, authenticated write
CREATE POLICY "Enable read access for all users" ON buildings
  FOR SELECT USING (true);

CREATE POLICY "Enable write access for authenticated users" ON orders
  FOR INSERT WITH CHECK (true);
```

### 3. Backup Data

Supabase automatically backs up daily. To manually backup:

1. Go to **Backups** in Supabase dashboard
2. Click **Create backup**

---

## 🚨 Common Issues & Solutions

### Issue: Connection Refused

**Error:**
```
psycopg2.OperationalError: could not connect to server
```

**Solutions:**
1. ✅ Verify `DATABASE_URL` is correct
2. ✅ Check password doesn't have special chars requiring escaping
3. ✅ Verify `SUPABASE_MODE=true`
4. ✅ In Supabase, check project is running (not paused)

### Issue: Extension Not Found

**Error:**
```
did not find required extension: postgis
```

**Solution:**
1. In Supabase SQL Editor, run:
   ```sql
   CREATE EXTENSION postgis;
   ```

### Issue: Too Many Connections

**Error:**
```
too many connections
```

**Solution:**
1. Reduce `DB_POOL_SIZE` to `3` or `4`
2. Update `backend/.env`:
   ```
   DB_POOL_SIZE=3
   ```

### Issue: Timeout on Queries

**Error:**
```
timeout waiting for idle object
```

**Solution:**
1. Supabase free tier has connection limits
2. Options:
   - Use Supabase Pro ($25/month)
   - Implement query caching
   - Reduce `pool_size`
   - Contact Supabase support

---

## 📊 Supabase Tiers

| Feature | Free | Pro | Team |
|---------|------|-----|------|
| **Database Size** | 500 MB | 8 GB | 100 GB+ |
| **Connections** | 4 | 60 | 200+ |
| **Cost** | $0 | $25/mo | Custom |
| **PostGIS** | ✅ | ✅ | ✅ |
| **Auto-scaling** | ❌ | ✅ | ✅ |

**Recommended for AeroCorridor**: **Pro tier** ($25/month)

---

## 🌐 Production Deployment with Supabase

### 1. Update Backend/.env on Railway

Use **Supabase connection string** instead of local PostgreSQL:

```
DATABASE_URL=postgresql://postgres:***@xxx.supabase.co:5432/postgres
SUPABASE_MODE=true
DB_POOL_SIZE=5
```

### 2. Update Frontend/.streamlit/secrets.toml

```toml
API_URL="https://your-railway-backend.railway.app"
```

### 3. Initialize Supabase Tables

Run seed_db.py once after deployment:

```bash
railway run python seed_db.py
```

### 4. Monitor in Supabase

Go to **Supabase Dashboard → Logs** to monitor queries

---

## 🎯 Quick Reference

### Local PostgreSQL
```bash
# .env
DATABASE_URL=postgresql://postgres:password@localhost:5432/aerocorridor
SUPABASE_MODE=false
DB_POOL_SIZE=10
```

### Supabase
```bash
# .env
DATABASE_URL=postgresql://postgres:PASSWORD@PROJECT_ID.supabase.co:5432/postgres
SUPABASE_MODE=true
DB_POOL_SIZE=5
```

---

## 📚 Useful Links

- **Supabase Docs**: https://supabase.com/docs
- **PostGIS Docs**: https://postgis.net/documentation/
- **Connection Issues**: https://supabase.com/docs/guides/database/connecting-to-postgres
- **Pricing**: https://supabase.com/pricing

---

## 🎉 You're Ready!

Your AeroCorridor backend is now connected to Supabase! 🚀

**Next Steps:**
1. ✅ Set `DATABASE_URL` in `backend/.env`
2. ✅ Run `python seed_db.py` to load test data
3. ✅ Start backend: `python run.py`
4. ✅ Start frontend: `streamlit run app.py`
5. ✅ Deploy to Railway when ready

---

**Questions?** Check Supabase documentation or AeroCorridor docs/
