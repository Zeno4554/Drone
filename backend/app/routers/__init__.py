"""Initialize routers for FastAPI app."""

from . import buildings, delivery_nodes, orders, routes, map, telemetry, setup

__all__ = ["buildings", "delivery_nodes", "orders", "routes", "map", "telemetry", "setup"]
