"""
Location and Geographic Distance Module for SyncPulse.

Implements:
- Haversine straight-line distance calculation using Earth's mean radius (6371.0 km).
- Strict handling of missing, uncaptured, or invalid coordinates.
- Clear distinction: straight-line distance ONLY, never road distance or travel time.
- Coordinate validation and formatted display strings.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple

EARTH_RADIUS_KM = 6371.0


@dataclass
class Coordinates:
    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None
    source: str = "MANUAL_ENTRY"  # "GPS_CAPTURE" or "MANUAL_ENTRY"
    captured_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def is_valid_coordinate(lat: Optional[float], lon: Optional[float]) -> bool:
    """Validates that latitude and longitude are within standard geographical boundaries."""
    if lat is None or lon is None:
        return False
    try:
        f_lat = float(lat)
        f_lon = float(lon)
        return -90.0 <= f_lat <= 90.0 and -180.0 <= f_lon <= 180.0
    except (ValueError, TypeError):
        return False


def haversine_distance_km(
    lat1: Optional[float],
    lon1: Optional[float],
    lat2: Optional[float],
    lon2: Optional[float],
) -> Optional[float]:
    """
    Calculates the approximate straight-line distance in kilometers between two
    geographical points using the Haversine formula with Earth's mean radius = 6371.0 km.

    Returns:
        float: straight-line distance in kilometers rounded to 2 decimal places.
        None: if any of the coordinates are missing or invalid.
    """
    if not is_valid_coordinate(lat1, lon1) or not is_valid_coordinate(lat2, lon2):
        return None

    # Cast to float
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lon2) - float(lon1))

    # Haversine formula
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    # Clamp a to [0.0, 1.0] to prevent floating point domain errors with sqrt
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = EARTH_RADIUS_KM * c

    return round(distance, 2)


def format_distance_label(distance_km: Optional[float]) -> str:
    """
    Returns a clear, honest user-facing distance label.
    Explicitly labels straight-line distance, never implying road distance or walking time.
    """
    if distance_km is None:
        return "Distance unavailable"

    if distance_km < 1.0:
        meters = int(round(distance_km * 1000))
        return f"{meters} m (straight-line)"
    return f"{distance_km:.2f} km (straight-line)"
