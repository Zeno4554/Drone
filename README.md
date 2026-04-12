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
