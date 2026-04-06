"""Frontend setup and installation guide."""

# Frontend Setup Guide

## Prerequisites

1. **Python 3.10+**
   ```bash
   python --version
   ```

2. **Streamlit CLI installed**
   - Will be installed via requirements.txt

3. **Backend running**
   - Must have backend on http://localhost:8000 or configured URL

## Installation

### 1. Navigate to Frontend

```bash
cd d:\Drone\frontend
```

### 2. Create Virtual Environment

```bash
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

### 4. Setup Secrets

```bash
# Copy example file
copy .streamlit\secrets.toml.example .streamlit\secrets.toml

# Edit .streamlit\secrets.toml and set:
# API_URL = "http://localhost:8000"
```

### 5. Run Streamlit App

```bash
streamlit run app.py
```

The app will start at: **http://localhost:8501**

## Project Structure

```
frontend/
├── app.py                          # Main entry point
├── pages/
│   ├── 1_map_page.py              # Map & building selector
│   ├── 2_orders_page.py           # Order placement & tracking
│   └── 3_dashboard_page.py        # Fleet dashboard & controls
├── components/
│   └── map_renderer.py            # Folium map utilities
├── services/
│   └── api_client.py              # API client for backend
├── .streamlit/
│   ├── config.toml                # Streamlit UI configuration
│   └── secrets.toml               # API secrets (git-ignored)
├── requirements.txt               # Python dependencies
└── .gitignore
```

## Pages Overview

### 🗺️ Map Page (1_map_page.py)
- **Purpose**: Select buildings and delivery nodes
- **Features**:
  - Building selector dropdown
  - Delivery nodes for selected building
  - Interactive Folium map with markers
  - Node details (altitude, capacity, type)
  - GeoJSON, risk zones, obstacles on map
- **Output**: Select node for order placement

### 📦 Orders Page (2_orders_page.py)
- **Purpose**: Place orders and track deliveries
- **Tabs**:
  - 📝 Place Order: Select destination, payload weight
  - 🚚 Active Orders: Live tracking of in-transit orders
  - 📋 Order History: All orders with filters
- **Features**:
  - Payload weight validation against node capacity
  - Automatic route planning on order placement
  - Route metrics display (distance, duration, risk)
  - Order status tracking

### 📊 Dashboard Page (3_dashboard_page.py)
- **Purpose**: Operator fleet management
- **Features**:
  - Real-time drone positions on map
  - Live telemetry for all drones (altitude, speed, battery)
  - Emergency controls (RTH, Land)
  - Auto-refresh capability
  - Fleet health metrics

## Streamlit Features Used

1. **Multi-page app**: `pages/` folder with numbered pages
2. **Session state**: `st.session_state` for cross-page data
3. **Caching**: `@st.cache_data` for expensive operations
4. **Columns & Containers**: Layout organization
5. **Folium integration**: `streamlit-folium` for interactive maps
6. **WebSocket ready**: (WebSocket support via API client)

## Configuration

### config.toml - UI Customization

```toml
[theme]
primaryColor = "#7B68EE"           # Purple
backgroundColor = "#FFFFFF"        # White
secondaryBackgroundColor = "#F0F2F6" # Light gray
textColor = "#262730"              # Dark text
font = "sans serif"

[client]
showErrorDetails = true            # Dev mode

[logger]
level = "info"                     # Log level

[server]
maxUploadSize = 200                # MB
enableXsrfProtection = true        # Security
```

### secrets.toml - API Configuration

```toml
API_URL = "http://localhost:8000"
```

For production:
```toml
API_URL = "https://aerocorridor-backend.railway.app"
AUTH_TOKEN = "your_api_token"
```

## API Client

`services/api_client.py` provides a Python wrapper for the FastAPI backend:

```python
from services.api_client import APIClient

api = APIClient("http://localhost:8000")

# Buildings
buildings = api.get_buildings()
building = api.get_building("BLD_PHOENIX_MALL")

# Delivery Nodes
nodes = api.get_delivery_nodes("BLD_PHOENIX_MALL")
node = api.get_delivery_node("NODE_PHX_ROOFTOP_1")

# Orders
api.place_order("NODE_PHX_ROOFTOP_1", 1.5, "Medical supplies")
orders = api.get_orders()
api.update_order(order_id, status="in-transit")

# Routes
route = api.plan_route(12.9716, 77.5946, 980.0, "NODE_PHX_ROOFTOP_1")

# Telemetry
telemetry = api.get_current_telemetry()
drone_data = api.get_drone_telemetry("DRONE_000")
api.emergency_rth("DRONE_000", 12.9716, 77.5946, 950.0)

# Map Data
buildings_geojson = api.get_buildings_geojson()
nodes_geojson = api.get_nodes_geojson()
risk_geojson = api.get_risk_zones_geojson(min_risk=0.3)
```

## Map Rendering

`components/map_renderer.py` provides Folium utilities:

```python
from components.map_renderer import (
    create_base_map,
    add_buildings_to_map,
    add_delivery_nodes_to_map,
    add_route_to_map,
    add_drone_position_to_map
)

# Create map
map_obj = create_base_map(center_lat=13.0, center_lon=77.6, zoom=12)

# Add layers
add_buildings_to_map(map_obj, buildings_geojson)
add_delivery_nodes_to_map(map_obj, nodes_geojson)
add_route_to_map(map_obj, waypoints)
add_drone_position_to_map(map_obj, drone_data)

# Display in Streamlit
import streamlit_folium as stf
stf.folium_static(map_obj)
```

## Styling & Customization

### Add Custom CSS

```python
st.markdown("""
    <style>
    .main-title { font-size: 3em; color: #7B68EE; }
    .status-card { padding: 20px; background: #F0F2F6; }
    </style>
""", unsafe_allow_html=True)
```

### Color Scheme

- Primary: `#7B68EE` (Medium Purple)
- Danger: `#FF0000` (Red)
- Success: `#00AA33` (Green)
- Warning: `#FFAA00` (Orange)

## Common Issues

### ModuleNotFoundError: No module named 'streamlit'

```bash
pip install -r requirements.txt
```

### ModuleNotFoundError: No module named 'folium'

```bash
pip install folium streamlit-folium
```

### ConnectionError: Backend not responding

Check:
1. Backend running: http://localhost:8000/health
2. Correct API_URL in `.streamlit/secrets.toml`
3. Firewall not blocking localhost:8000

### Page not loading

- Clear Streamlit cache: `streamlit cache clear`
- Check `.streamlit/secrets.toml` exists
- Restart: `streamlit run app.py`

## Local Testing

### Test Backend Connection

```python
import requests
resp = requests.get("http://localhost:8000/health")
print(resp.json())  # Should show {"status": "healthy"}
```

### Test API Client

```python
from services.api_client import APIClient

api = APIClient("http://localhost:8000")
buildings = api.get_buildings()
print(buildings)  # Should list 5 buildings
```

### Test Individual Page

```bash
streamlit run pages/1_map_page.py
```

## Deployment to Streamlit Cloud

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Frontend ready for deployment"
   git push
   ```

2. **Connect to Streamlit Cloud**
   - Go to: https://share.streamlit.io/
   - "New app" → GitHub repo
   - Branch: `main`
   - Root directory: `frontend`

3. **Set Secrets**
   - In Streamlit Cloud dashboard:
   - Click "Settings" → "Secrets"
   - Paste:
     ```
     API_URL = "https://your-railway-backend.railway.app"
     ```

4. **Deploy**
   - Streamlit deploys automatically on git push
   - View logs in dashboard

## Performance Tips

1. **Cache expensive operations**
   ```python
   @st.cache_data
   def load_buildings():
       return api.get_buildings()
   ```

2. **Use columns for layout**
   ```python
   col1, col2, col3 = st.columns(3)
   with col1: st.metric("Metric", value)
   ```

3. **Lazy load map data**
   ```python
   if st.checkbox("Show risk zones"):
       risk_data = api.get_risk_zones_geojson()
   ```

4. **Limit dataframe size**
   ```python
   st.dataframe(df.head(100), use_container_width=True)
   ```

## Environment Variables for Production

```bash
API_URL=https://aerocorridor-backend.railway.app
```

## Next Steps

1. ✅ Frontend running on http://localhost:8501
2. 🔗 Verify backend connection (check sidebar)
3. 🗺️ Test Map page functionality
4. 📦 Test Order placement
5. 🚀 Deploy to Streamlit Cloud

---

For issues: Check browser console (F12) and Streamlit terminal for error messages.
