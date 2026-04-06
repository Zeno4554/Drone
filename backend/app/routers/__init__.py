"""Initialize routers for FastAPI app."""

from . import buildings, delivery_nodes, orders, routes, map, telemetry

__all__ = ["buildings", "delivery_nodes", "orders", "routes", "map", "telemetry"]
