"""Server-controlled pilot fare estimation for passenger rides.

Distance is estimated from coordinates, not a road-routing provider. The
route multiplier and fare rates are configurable via environment variables;
replace this estimator with a routing provider before relying on it for
precise ETAs or guaranteed fares.
"""
from decimal import Decimal, ROUND_HALF_UP
from math import asin, cos, radians, sin, sqrt
import os

from django.conf import settings


EARTH_RADIUS_KM = 6371.0088


def _decimal_setting(name, default):
    value = os.getenv(name, str(default))
    try:
        parsed = Decimal(value)
    except Exception as exc:
        raise ValueError(f"{name} must be a valid decimal amount.") from exc
    if not parsed.is_finite() or parsed < 0:
        raise ValueError(f"{name} must be a finite, non-negative amount.")
    return parsed


def haversine_distance_km(latitude_a, longitude_a, latitude_b, longitude_b):
    """Return straight-line distance between two coordinate pairs in km."""
    lat_a, lon_a, lat_b, lon_b = map(
        lambda value: radians(float(value)),
        (latitude_a, longitude_a, latitude_b, longitude_b),
    )
    lat_delta = lat_b - lat_a
    lon_delta = lon_b - lon_a
    haversine = (
        sin(lat_delta / 2) ** 2
        + cos(lat_a) * cos(lat_b) * sin(lon_delta / 2) ** 2
    )
    # Floating-point rounding can make the value slightly exceed 1.
    haversine = min(1.0, max(0.0, haversine))
    return 2 * EARTH_RADIUS_KM * asin(sqrt(haversine))


def estimate_ride_distance_km(
    pickup_latitude,
    pickup_longitude,
    destination_latitude,
    destination_longitude,
):
    straight_line_km = haversine_distance_km(
        pickup_latitude,
        pickup_longitude,
        destination_latitude,
        destination_longitude,
    )
    multiplier = _decimal_setting("RIDE_ROUTE_DISTANCE_MULTIPLIER", "1.30")
    return (Decimal(str(straight_line_km)) * multiplier).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def quote_ride_fare(vehicle_type, estimated_distance_km):
    """Compute a server-side NGN estimate; never trust a client-supplied fare."""
    if vehicle_type == "CAR":
        base_fare = _decimal_setting("RIDE_CAR_BASE_FARE_NGN", "500")
        per_km = _decimal_setting("RIDE_CAR_PER_KM_FARE_NGN", "250")
    elif vehicle_type == "MOTORCYCLE":
        base_fare = _decimal_setting("RIDE_MOTORCYCLE_BASE_FARE_NGN", "300")
        per_km = _decimal_setting("RIDE_MOTORCYCLE_PER_KM_FARE_NGN", "150")
    else:
        raise ValueError("Unsupported ride vehicle type.")

    fare = base_fare + (per_km * estimated_distance_km)
    return fare.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def quote_for_location_data(data):
    distance_km = estimate_ride_distance_km(
        data["pickup_latitude"],
        data["pickup_longitude"],
        data["destination_latitude"],
        data["destination_longitude"],
    )
    return {
        "estimated_distance_km": distance_km,
        "quoted_fare": quote_ride_fare(data["vehicle_type"], distance_km),
        "currency": "NGN",
        "is_estimate": True,
    }
