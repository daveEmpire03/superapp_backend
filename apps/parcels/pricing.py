"""Configurable pilot parcel pricing; distance is a straight-line estimate."""
from decimal import Decimal, ROUND_HALF_UP
import os

from apps.rides.pricing import estimate_ride_distance_km


def _rate(name, default):
    try:
        value = Decimal(os.getenv(name, default))
    except Exception as exc:
        raise ValueError(f"{name} must be a valid decimal.") from exc
    if not value.is_finite() or value < 0:
        raise ValueError(f"{name} must be finite and non-negative.")
    return value


def quote_parcel(data):
    distance = estimate_ride_distance_km(
        data["pickup_latitude"],
        data["pickup_longitude"],
        data["destination_latitude"],
        data["destination_longitude"],
    )
    base = _rate("PARCEL_BASE_FARE_NGN", "500")
    per_km = _rate("PARCEL_PER_KM_FARE_NGN", "180")
    package_fee = {
        "DOCUMENT": Decimal("0"),
        "SMALL": Decimal("100"),
        "MEDIUM": Decimal("300"),
        "LARGE": Decimal("700"),
    }[data["package_size"]]
    fare = (base + per_km * distance + package_fee).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return {
        "estimated_distance_km": distance,
        "quoted_fare": fare,
        "currency": "NGN",
        "is_estimate": True,
    }
