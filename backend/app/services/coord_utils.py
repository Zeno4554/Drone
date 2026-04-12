"""
Coordinate conversion utilities.

Converts between geographic (lat/lon) and local Cartesian metres
using a flat-earth approximation — accurate to < 0.1 % within 100 km.

Used by the swarm simulation to accept map-click coordinates from the
frontend and to attach lat/lon to every streamed frame for Leaflet display.
"""

from __future__ import annotations
import math

# Metres per degree of latitude (constant everywhere)
_M_PER_DEG_LAT = 111_320.0


def latlon_to_metres(
    lat: float, lon: float, ref_lat: float, ref_lon: float
) -> tuple[float, float]:
    """
    Convert (lat, lon) → local (x_east_m, y_north_m) relative to (ref_lat, ref_lon).
    """
    cos_ref = math.cos(math.radians(ref_lat))
    x = (lon - ref_lon) * _M_PER_DEG_LAT * cos_ref
    y = (lat - ref_lat) * _M_PER_DEG_LAT
    return x, y


def metres_to_latlon(
    x: float, y: float, ref_lat: float, ref_lon: float
) -> tuple[float, float]:
    """
    Convert local (x_east_m, y_north_m) → (lat, lon) given reference origin.
    """
    cos_ref = math.cos(math.radians(ref_lat))
    lat = ref_lat + y / _M_PER_DEG_LAT
    lon = ref_lon + x / (_M_PER_DEG_LAT * cos_ref)
    return lat, lon


def centroid(points_latlon: list[list[float]]) -> tuple[float, float]:
    """
    Return the geographic centroid (avg lat, avg lon) of a set of points.
    Used to pick the local coordinate origin.
    """
    lats = [p[0] for p in points_latlon]
    lons = [p[1] for p in points_latlon]
    return sum(lats) / len(lats), sum(lons) / len(lons)


def points_to_local_scale(
    points_latlon: list[list[float]],
    ref_lat: float,
    ref_lon: float,
    target_size: float = 1000.0,
) -> tuple[list[tuple[float, float]], float]:
    """
    Convert a list of lat/lon points to local metres and return a scale factor
    so that the bounding box fits inside [0, target_size].

    Returns
    -------
    local_pts : list of (x_m, y_m) — unscaled local metre coordinates
    scale     : multiply x_m / y_m by this to map into [0, target_size]
                (1.0 means points already fit; > 1.0 means the area is smaller
                 than target_size and we upscale; handled by caller)
    """
    local = [latlon_to_metres(p[0], p[1], ref_lat, ref_lon) for p in points_latlon]
    if not local:
        return local, 1.0
    xs = [p[0] for p in local]
    ys = [p[1] for p in local]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
    scale = target_size / span
    return local, scale


def build_coord_mapper(
    ref_lat: float,
    ref_lon: float,
    ref_x_offset: float = 0.0,
    ref_y_offset: float = 0.0,
):
    """
    Return a pair of callables (to_sim, from_sim) that convert between
    lat/lon and simulation metres, applying a fixed offset so that the
    point cloud is centred nicely within the simulation area.

    to_sim(lat, lon) -> (x_m, y_m)
    from_sim(x_m, y_m) -> (lat, lon)
    """
    def to_sim(lat: float, lon: float) -> tuple[float, float]:
        x, y = latlon_to_metres(lat, lon, ref_lat, ref_lon)
        return x + ref_x_offset, y + ref_y_offset

    def from_sim(x: float, y: float) -> tuple[float, float]:
        return metres_to_latlon(x - ref_x_offset, y - ref_y_offset, ref_lat, ref_lon)

    return to_sim, from_sim
