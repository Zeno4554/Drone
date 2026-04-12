"""Initialize routers for FastAPI app."""

from . import buildings, delivery_nodes, map, orders, routes, setup, swarm_hybrid, swarm_obstacles, telemetry

__all__ = [
    "buildings",
    "delivery_nodes",
    "map",
    "orders",
    "routes",
    "setup",
    "swarm_hybrid",
    "swarm_obstacles",
    "telemetry",
]
