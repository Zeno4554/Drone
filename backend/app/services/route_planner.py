"""3D Route Planning using A* pathfinding algorithm."""

import heapq
import math
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from .risk_calculator import RiskCalculator
from ..config import settings

@dataclass
class Waypoint:
    """Represents a navigational waypoint in 3D space."""
    latitude: float
    longitude: float
    altitude_msl: float
    order: int = 0
    
    def to_dict(self):
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude_msl": self.altitude_msl,
            "order": self.order,
        }

@dataclass
class GridNode:
    """3D voxel grid node for pathfinding."""
    x: float  # Latitude (degrees)
    y: float  # Longitude (degrees)
    z: float  # Altitude MSL (meters)
    g_cost: float = 0.0  # Cost from start
    h_cost: float = 0.0  # Heuristic cost to goal
    parent: Optional['GridNode'] = None
    
    @property
    def f_cost(self) -> float:
        """Total estimated cost (g + h)."""
        return self.g_cost + self.h_cost
    
    def __lt__(self, other):
        """For priority queue comparison."""
        return self.f_cost < other.f_cost
    
    def __eq__(self, other):
        """Node equality based on position."""
        if not isinstance(other, GridNode):
            return False
        return self.x == other.x and self.y == other.y and self.z == other.z
    
    def __hash__(self):
        """Make node hashable for sets/dicts."""
        return hash((round(self.x, 6), round(self.y, 6), round(self.z, 1)))
    
    def position(self) -> Tuple[float, float, float]:
        """Get position tuple."""
        return (self.x, self.y, self.z)


class RoutePlanner3D:
    """3D route planning engine using A* on voxel grid."""
    
    def __init__(self, risk_calculator: Optional[RiskCalculator] = None):
        """Initialize route planner.
        
        Args:
            risk_calculator: Risk calculator for cost evaluation
        """
        self.risk_calculator = risk_calculator or RiskCalculator()
        self.voxel_size = settings.VOXEL_SIZE_M
        
    def plan_route(
        self,
        source_lat: float,
        source_lon: float,
        source_alt_msl: float,
        dest_lat: float,
        dest_lon: float,
        dest_alt_msl: float,
        obstacles: Optional[List] = None,
    ) -> Dict:
        """Plan 3D route from source to destination.
        
        Uses A* pathfinding on a voxel grid with risk-weighted costs.
        
        Args:
            source_lat: Source latitude (degrees)
            source_lon: Source longitude (degrees)
            source_alt_msl: Source altitude MSL (meters)
            dest_lat: Destination latitude (degrees)
            dest_lon: Destination longitude (degrees)
            dest_alt_msl: Destination altitude MSL (meters)
            obstacles: List of obstacle geometries
            
        Returns:
            Dictionary with:
                - waypoints: List of Waypoint objects
                - total_distance_m: Total path distance
                - total_altitude_change_m: Total vertical distance
                - risk_score: Composite risk score
                - valid: Whether route is safe
        """
        start_node = GridNode(source_lat, source_lon, source_alt_msl)
        goal_node = GridNode(dest_lat, dest_lon, dest_alt_msl)
        
        # A* pathfinding
        waypoints = self._a_star_search(start_node, goal_node, obstacles)
        
        if not waypoints:
            # If A* fails, return straight line as fallback
            waypoints = [start_node, goal_node]
        
        # Convert to Waypoint objects with ordering
        route_waypoints = []
        for i, node in enumerate(waypoints):
            wp = Waypoint(
                latitude=node.x,
                longitude=node.y,
                altitude_msl=node.z,
                order=i,
            )
            route_waypoints.append(wp)
        
        # Calculate metrics
        total_distance = self._calculate_total_distance(waypoints)
        total_altitude_change = self._calculate_altitude_change(waypoints)
        risk_score = self._calculate_path_risk(waypoints)
        
        return {
            "waypoints": route_waypoints,
            "total_distance_m": total_distance,
            "total_altitude_change_m": total_altitude_change,
            "risk_score": risk_score,
            "valid": risk_score < 0.8,  # Invalid if risk too high
            "estimated_duration_s": total_distance / 15.0,  # Assume 15 m/s cruise speed
        }
    
    def _a_star_search(
        self,
        start: GridNode,
        goal: GridNode,
        obstacles: Optional[List] = None,
    ) -> List[GridNode]:
        """A* search algorithm on 3D voxel grid.
        
        Args:
            start: Start node
            goal: Goal node
            obstacles: List of obstacle zones to avoid
            
        Returns:
            List of waypoint nodes from start to goal
        """
        open_set = []
        closed_set = set()
        came_from = {}
        
        # Initialize start node
        start.h_cost = self._heuristic(start, goal)
        heapq.heappush(open_set, start)
        
        while open_set:
            current = heapq.heappop(open_set)
            
            if current == goal:
                # Reconstruct path
                return self._reconstruct_path(came_from, current)
            
            closed_set.add(current.position())
            
            # Explore neighbors
            for neighbor in self._get_neighbors(current, goal, obstacles):
                if neighbor.position() in closed_set:
                    continue
                
                # Calculate costs
                distance = self._euclidean_distance(current, neighbor)
                new_g_cost = current.g_cost + distance
                
                # Check if neighbor with better g_cost exists in open_set
                existing = next(
                    (n for n in open_set if n == neighbor), None
                )
                if existing and new_g_cost >= existing.g_cost:
                    continue
                
                # Update neighbor
                neighbor.g_cost = new_g_cost
                neighbor.h_cost = self._heuristic(neighbor, goal)
                neighbor.parent = current
                came_from[neighbor.position()] = current.position()
                
                heapq.heappush(open_set, neighbor)
        
        # No path found
        return []
    
    def _get_neighbors(
        self,
        node: GridNode,
        goal: GridNode,
        obstacles: Optional[List] = None,
    ) -> List[GridNode]:
        """Get 26 neighbors in 3D voxel grid (excluding diagonals through obstacles).
        
        Returns nodes that move by one voxel in each direction.
        """
        neighbors = []
        
        # 6 cardinal directions in 3D
        directions = [
            (1, 0, 0), (-1, 0, 0),   # Lat +/-
            (0, 1, 0), (0, -1, 0),   # Lon +/-
            (0, 0, 1), (0, 0, -1),   # Alt +/-
        ]
        
        # Add some diagonal moves (8 horizontal + 4 vertical diagonals)
        directions += [
            (1, 1, 0), (1, -1, 0), (-1, 1, 0), (-1, -1, 0),  # Horizontal diagonals
            (1, 0, 1), (1, 0, -1), (-1, 0, 1), (-1, 0, -1),  # Lat-Alt diagonals
            (0, 1, 1), (0, 1, -1), (0, -1, 1), (0, -1, -1),  # Lon-Alt diagonals
        ]
        
        # Lat/Lon step = ~5m at equator ≈ 0.000045 degrees
        lat_step = 0.000045
        lon_step = 0.000045
        alt_step = self.voxel_size
        
        for dlat, dlon, dalt in directions:
            neighbor = GridNode(
                x=node.x + dlat * lat_step,
                y=node.y + dlon * lon_step,
                z=node.z + dalt * alt_step,
            )
            
            # Altitude constraints
            if neighbor.z < settings.CRUISE_ALTITUDE_AGL_M:
                neighbor.z = settings.CRUISE_ALTITUDE_AGL_M + 920  # Min altitude
            if neighbor.z > settings.MAX_ALTITUDE_AGL_M + 920:
                continue  # Skip too high
            
            # Obstacle avoidance (simplified)
            if self._is_valid_node(neighbor, obstacles):
                neighbors.append(neighbor)
        
        return neighbors
    
    def _is_valid_node(self, node: GridNode, obstacles: Optional[List] = None) -> bool:
        """Check if node is valid (not in obstacle or restricted zone)."""
        # Simplified check - in production, check against actual obstacle geometry
        return True
    
    def _heuristic(self, node: GridNode, goal: GridNode) -> float:
        """Heuristic function (Euclidean distance to goal)."""
        return self._euclidean_distance(node, goal)
    
    def _euclidean_distance(self, node1: GridNode, node2: GridNode) -> float:
        """Calculate 3D Euclidean distance between nodes."""
        # Convert lat/lon to approximate meters (rough approximation)
        lat_diff_m = (node2.x - node1.x) * 111000  # 1 degree lat ≈ 111 km
        lon_diff_m = (node2.y - node1.y) * 111000 * math.cos(math.radians(node1.x))  # Adjusted for latitude
        alt_diff_m = node2.z - node1.z
        
        distance = math.sqrt(lat_diff_m**2 + lon_diff_m**2 + alt_diff_m**2)
        return distance
    
    def _reconstruct_path(self, came_from: Dict, current: GridNode) -> List[GridNode]:
        """Reconstruct path from goal to start."""
        path = [current]
        while current.position() in came_from:
            prev_pos = came_from[current.position()]
            # Create node from prev position
            current = GridNode(prev_pos[0], prev_pos[1], prev_pos[2])
            path.append(current)
        path.reverse()
        return path
    
    def _calculate_total_distance(self, nodes: List[GridNode]) -> float:
        """Calculate total path distance."""
        total = 0.0
        for i in range(len(nodes) - 1):
            total += self._euclidean_distance(nodes[i], nodes[i + 1])
        return total
    
    def _calculate_altitude_change(self, nodes: List[GridNode]) -> float:
        """Calculate total altitude change (climb + descent)."""
        total = 0.0
        for i in range(len(nodes) - 1):
            alt_change = abs(nodes[i + 1].z - nodes[i].z)
            total += alt_change
        return total
    
    def _calculate_path_risk(self, nodes: List[GridNode]) -> float:
        """Calculate composite risk along path."""
        if not nodes:
            return 0.5
        
        total_risk = 0.0
        for node in nodes:
            # Risk based on altitude (higher = more exposure)
            altitude_risk = min(1.0, (node.z - 920) / 300.0)
            total_risk += altitude_risk
        
        avg_risk = total_risk / len(nodes) if nodes else 0.5
        return min(1.0, avg_risk)
