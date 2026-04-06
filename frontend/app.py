"""Main Streamlit app entry point - Home / About page."""

import streamlit as st

# Page config
st.set_page_config(
    page_title="AeroCorridor",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Add custom CSS
st.markdown("""
    <style>
    .main-title {
        font-size: 3em;
        font-weight: bold;
        color: #7B68EE;
        text-align: center;
        margin-bottom: 30px;
    }
    .status-card {
        padding: 20px;
        border-radius: 10px;
        background-color: #F0F2F6;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar info
st.sidebar.title("🚁 AeroCorridor")
st.sidebar.write("3D Drone Delivery Navigation System")

# Get API URL from secrets
api_url = st.secrets.get("API_URL", "http://localhost:8000")

st.sidebar.divider()
st.sidebar.write("**System Status**")

# Try to connect to backend
try:
    import requests
    resp = requests.get(f"{api_url}/health", timeout=2)
    if resp.status_code == 200:
        st.sidebar.success("✅ Backend: Connected")
    else:
        st.sidebar.warning("⚠️ Backend: Error")
except Exception:
    st.sidebar.error("❌ Backend: Offline")

# ---- Home / About page content ----
st.markdown('<h1 class="main-title">🚁 AeroCorridor</h1>', unsafe_allow_html=True)

st.markdown("""
### About This System

**AeroCorridor** is a cutting-edge 3D drone delivery navigation system designed for urban air mobility. 
It provides:

- **3D Route Planning**: MSL-normalized altitude-aware pathfinding using A* algorithm
- **Real-time Tracking**: Live drone telemetry and position updates
- **Risk Assessment**: 5-tier risk zone visualization (Green/Grey/Yellow/Red/Black)
- **Operator Dashboard**: Fleet management and emergency controls
- **Building Integration**: Delivery nodes on rooftops, balconies, docks

### Technical Stack

- **Frontend**: Streamlit (Python web UI)
- **Backend**: FastAPI (REST + WebSocket)
- **Database**: PostgreSQL + PostGIS (Spatial queries)
- **Deployment**: Railway.app + Streamlit Cloud

### Demo Data

This system is pre-populated with test data for Bengaluru:

- 5 test buildings
- 5 delivery nodes
- Risk zones around airports
- Obstacle data (communication towers, power lines)

### Quick Start

1. **Place Order**: Go to 📦 Orders and select a building → delivery node
2. **Plan Route**: System automatically plans 3D route avoiding obstacles
3. **Track Drone**: Go to 📊 Dashboard to see real-time drone positions
4. **Emergency Controls**: Emergency RTH, Land, Hover commands available

### Contacts & Support

GitHub: [AeroCorridor](https://github.com/yourusername/aerocorridor)

Developed for: International Drone Expo 2026
""")

st.divider()
st.info("🚀 **Expo Demo**: April 17, 2026")
