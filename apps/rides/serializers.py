from decimal import Decimal

from rest_framework import serializers

from .models import Ride, RideDriverProfile, RideStatusHistory
from .pricing import haversine_distance_km


class RideLocationInputSerializer(serializers.Serializer):
    vehicle_type = serializers.ChoiceField(choices=Ride.VehicleType.choices)
    pickup_address = serializers.CharField(max_length=255, trim_whitespace=True)
    pickup_latitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        min_value=-90,
        max_value=90,
    )
    pickup_longitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        min_value=-180,
        max_value=180,
    )
    destination_address = serializers.CharField(max_length=255, trim_whitespace=True)
    destination_latitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        min_value=-90,
        max_value=90,
    )
    destination_longitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        min_value=-180,
        max_value=180,
    )

    def validate_pickup_address(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Pickup address is required.")
        return value

    def validate_destination_address(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Destination address is required.")
        return value

    def validate(self, attrs):
        straight_line_distance_km = haversine_distance_km(
            attrs["pickup_latitude"],
            attrs["pickup_longitude"],
            attrs["destination_latitude"],
            attrs["destination_longitude"],
        )
        if Decimal(str(straight_line_distance_km)) < Decimal("0.05"):
            raise serializers.ValidationError(
                {"destination": "Pickup and destination must be at least 50 metres apart."}
            )
        return attrs


class RideQuoteRequestSerializer(RideLocationInputSerializer):
    """Input for a non-persisting quote request."""


class RideCreateSerializer(RideLocationInputSerializer):
    payment_method = serializers.ChoiceField(choices=Ride.PaymentMethod.choices)
    passenger_note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        trim_whitespace=True,
    )


class RideStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = RideStatusHistory
        fields = ("status", "note", "changed_by_name", "created_at")
        read_only_fields = fields

    def get_changed_by_name(self, obj):
        if obj.changed_by is None:
            return None
        return obj.changed_by.get_full_name().strip() or obj.changed_by.email


class RideSerializer(serializers.ModelSerializer):
    driver_name = serializers.SerializerMethodField()
    status_history = RideStatusHistorySerializer(many=True, read_only=True)
    estimated_distance_km = serializers.SerializerMethodField()
    is_fare_estimate = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = (
            "id",
            "vehicle_type",
            "status",
            "pickup_address",
            "pickup_latitude",
            "pickup_longitude",
            "destination_address",
            "destination_latitude",
            "destination_longitude",
            "estimated_distance_km",
            "quoted_fare",
            "currency",
            "is_fare_estimate",
            "payment_method",
            "payment_status",
            "driver",
            "driver_name",
            "requested_at",
            "driver_assigned_at",
            "trip_started_at",
            "trip_completed_at",
            "cancelled_at",
            "passenger_note",
            "status_history",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_driver_name(self, obj):
        if obj.driver is None:
            return None
        return obj.driver.get_full_name().strip() or obj.driver.email

    def get_estimated_distance_km(self, obj):
        from .pricing import estimate_ride_distance_km

        return estimate_ride_distance_km(
            obj.pickup_latitude,
            obj.pickup_longitude,
            obj.destination_latitude,
            obj.destination_longitude,
        )

    def get_is_fare_estimate(self, obj):
        # The pilot quote is approximate until road routing is integrated.
        return True


class RideDriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideDriverProfile
        fields = (
            "vehicle_type",
            "vehicle_plate",
            "vehicle_make",
            "vehicle_color",
            "is_available",
            "is_approved",
            "is_suspended",
            "current_latitude",
            "current_longitude",
            "last_location_at",
        )
        read_only_fields = (
            "is_available",
            "is_approved",
            "is_suspended",
            "current_latitude",
            "current_longitude",
            "last_location_at",
        )

    def validate_vehicle_plate(self, value):
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("Vehicle plate is required.")
        return value


class DriverLocationSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(
        max_digits=10, decimal_places=7, min_value=-90, max_value=90
    )
    longitude = serializers.DecimalField(
        max_digits=10, decimal_places=7, min_value=-180, max_value=180
    )


class DriverAvailabilitySerializer(serializers.Serializer):
    is_available = serializers.BooleanField()

class DriverRideStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(
            (Ride.Status.DRIVER_ARRIVING, Ride.Status.DRIVER_ARRIVING),
            (Ride.Status.IN_PROGRESS, Ride.Status.IN_PROGRESS),
            (Ride.Status.COMPLETED, Ride.Status.COMPLETED),
        )
    )
