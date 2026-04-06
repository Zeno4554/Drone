"""Risk calculation and voxel grid management."""

import math
from typing import List, Dict, Tuple, Optional
from ..config import settings


class RiskCalculator:
    """Calculates risk scores for drone operations."""
    
    def __init__(self):
        """Initialize risk calculator."""
        self.voxel_size = settings.VOXEL_SIZE_M
        self.bengaluru_baseline = settings.BENGALURU_GROUND_ELEV_MSL
    
    def calculate_composite_risk(
        self,
        latitude: float,
        longitude: float,
        altitude_msl: float,
        obstacles: Optional[List] = None,
        air_traffic_density: float = 0.1,
        wind_speed_ms: float = 5.0,
    ) -> Tuple[float, str]:
        """Calculate composite risk score for a position.
        
        Args:
            latitude: Latitude (degrees)
            longitude: Longitude (degrees)
            altitude_msl: Altitude MSL (meters)
            obstacles: List of nearby obstacles
            air_traffic_density: Relative air traffic density (0-1)
            wind_speed_ms: Wind speed in m/s
            
        Returns:
            Tuple of (risk_score, zone_color)
                - risk_score: 0.0 (safe) to 1.0 (dangerous)
                - zone_color: 'green', 'grey', 'yellow', 'red', or 'black'
        """
        # Component risk scores
        obstacles_risk = self._calculate_obstacle_risk(
            latitude, longitude, altitude_msl, obstacles
        )
        altitude_risk = self._calculate_altitude_risk(altitude_msl)
        air_traffic_risk = self._calculate_air_traffic_risk(
            latitude, longitude, altitude_msl, air_traffic_density
        )
        wind_risk = self._calculate_wind_risk(wind_speed_ms)
        
        # Weighted composite
        composite_risk = (
            0.4 * obstacles_risk +
            0.2 * altitude_risk +
            0.2 * air_traffic_risk +
            0.2 * wind_risk
        )
        
        composite_risk = min(1.0, max(0.0, composite_risk))
        zone_color = self._risk_to_color(composite_risk)
        
        return composite_risk, zone_color
    
    def _calculate_obstacle_risk(
        self,
        latitude: float,
        longitude: float,
        altitude_msl: float,
        obstacles: Optional[List] = None,
    ) -> float:
        """Calculate risk from nearby obstacles."""
        if not obstacles:
            return 0.1  # Base obstacle risk in urban area
        
        min_distance = float('inf')
        for obs in obstacles:
            # Simplified distance calculation
            distance = self._calculate_3d_distance(
                latitude, longitude, altitude_msl,
                obs.get('lat'), obs.get('lon'), obs.get('alt_msl')
            )
            min_distance = min(min_distance, distance)
        
        # Risk inversely proportional to distance
        if min_distance < 10:  # Less than 10m away
            return 0.9
        elif min_distance < 50:
            return 0.5
        else:
            return 0.1
    
    def _calculate_altitude_risk(self, altitude_msl: float) -> float:
        """Calculate risk based on altitude.
        
        - Low altitude (0-50m AGL): Crowded with buildings, high risk
        - Medium altitude (50-150m AGL): Normal operation, medium risk
        - High altitude (>150m AGL): Less obstacles, lower risk
        """
        altitude_agl = altitude_msl - self.bengaluru_baseline
        
        if altitude_agl < 30:
            return 0.8  # Too low, building collision risk
        elif altitude_agl < 60:
            return 0.5  # Low altitude ops
        elif altitude_agl < 150:
            return 0.2  # Optimal altitude
        else:
            return 0.3  # High altitude, thin air concerns
    
    def _calculate_air_traffic_risk(
        self,
        latitude: float,
        longitude: float,
        altitude_msl: float,
        air_traffic_density: float = 0.1,
    ) -> float:
        """Calculate risk from manned aircraft."""
        # In Bengaluru, major air corridors around airports
        # DIN (Devanahalli) at ~500-5000 ft, HAL at similar
        
        # Simulate restricted zones (rough coordinates)
        restricted_zones = [
            {"lat": 13.2012, "lon": 77.7062, "radius_km": 20},  # Devanahalli Airport
            {"lat": 12.9444, "lon": 77.6499, "radius_km": 10},  # HAL Airport
        ]
        
        for zone in restricted_zones:
            distance = self._calculate_distance_to_point(
                latitude, longitude,
                zone['lat'], zone['lon']
            )
            if distance < zone['radius_km']:
                # In restricted zone - apply traffic density
                return min(0.8, 0.3 + air_traffic_density)
        
        # Outside restricted zones, low air traffic risk
        return air_traffic_density * 0.2
    
    def _calculate_wind_risk(self, wind_speed_ms: float) -> float:
        """Calculate risk from wind."""
        # DroneS typically handle up to 10-12 m/s (36-43 km/h)
        if wind_speed_ms < 5:
            return 0.1
        elif wind_speed_ms < 10:
            return 0.3
        elif wind_speed_ms < 15:
            return 0.6
        else:
            return 0.9
    
    def _risk_to_color(self, risk_score: float) -> str:
        """Convert risk score to zone color."""
        if risk_score <= 0.2:
            return "green"
        elif risk_score <= 0.4:
            return "grey"
        elif risk_score <= 0.6:
            return "yellow"
        elif risk_score <= 0.8:
            return "red"
        else:
            return "black"
    
    def _calculate_3d_distance(
        self,
        lat1: float, lon1: float, alt1: float,
        lat2: float, lon2: float, alt2: float,
    ) -> float:
        """Calculate 3D distance in meters."""
        # Horizontal distance (Haversine)
        horiz_dist = self._calculate_distance_to_point(lat1, lon1, lat2, lon2)
        horiz_dist_m = horiz_dist * 1000  # Convert km to m
        
        # Vertical distance
        vert_dist = abs(alt2 - alt1)
        
        # 3D distance
        return math.sqrt(horiz_dist_m**2 + vert_dist**2)
    
    def _calculate_distance_to_point(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points using Haversine (returns km)."""
        R = 6371  # Earth radius in km
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * \
            math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def generate_risk_heatmap(
        self,
        bounds: Dict,  # {"min_lat", "max_lat", "min_lon", "max_lon", "min_alt", "max_alt"}
        grid_size: int = 10,
    ) -> List[Dict]:
        """Generate risk heatmap grid for visualization.
        
        Args:
            bounds: Geographic bounds
            grid_size: Number of grid cells per dimension
            
        Returns:
            List of voxel data points with risk scores
        """
        voxels = []
        
        lat_step = (bounds['max_lat'] - bounds['min_lat']) / grid_size
        lon_step = (bounds['max_lon'] - bounds['min_lon']) / grid_size
        alt_step = (bounds['max_alt'] - bounds['min_alt']) / grid_size
        
        for i in range(grid_size):
            lat = bounds['min_lat'] + i * lat_step
            for j in range(grid_size):
                lon = bounds['min_lon'] + j * lon_step
                for k in range(grid_size):
                    alt = bounds['min_alt'] + k * alt_step
                    
                    risk_score, color = self.calculate_composite_risk(lat, lon, alt)
                    
                    voxels.append({
                        "latitude": lat,
                        "longitude": lon,
                        "altitude_msl": alt,
                        "risk_score": risk_score,
                        "zone_color": color,
                    })
        
        return voxels
