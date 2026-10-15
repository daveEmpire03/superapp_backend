from decimal import Decimal

from rest_framework import serializers

from apps.rides.pricing import haversine_distance_km

from .models import ParcelShipment, ParcelStatusHistory


class ParcelLocationInputSerializer(serializers.Serializer):
    package_size = serializers.ChoiceField(choices=ParcelShipment.PackageSize.choices)
    package_description = serializers.CharField(max_length=500, trim_whitespace=True)
    recipient_name = serializers.CharField(max_length=150, trim_whitespace=True)
    recipient_phone = serializers.CharField(max_length=20, trim_whitespace=True)
    pickup_address = serializers.CharField(max_length=255, trim_whitespace=True)
    pickup_latitude = serializers.DecimalField(max_digits=10, decimal_places=7, min_value=-90, max_value=90)
    pickup_longitude = serializers.DecimalField(max_digits=10, decimal_places=7, min_value=-180, max_value=180)
    destination_address = serializers.CharField(max_length=255, trim_whitespace=True)
    destination_latitude = serializers.DecimalField(max_digits=10, decimal_places=7, min_value=-90, max_value=90)
    destination_longitude = serializers.DecimalField(max_digits=10, decimal_places=7, min_value=-180, max_value=180)

    def validate(self, attrs):
        for field in ("package_description", "recipient_name", "recipient_phone", "pickup_address", "destination_address"):
            attrs[field] = attrs[field].strip()
            if not attrs[field]:
                raise serializers.ValidationError({field: "This field is required."})
        distance = haversine_distance_km(
            attrs["pickup_latitude"], attrs["pickup_longitude"],
            attrs["destination_latitude"], attrs["destination_longitude"],
        )
        if Decimal(str(distance)) < Decimal("0.05"):
            raise serializers.ValidationError({"destination_address": "Pickup and destination must be at least 50 metres apart."})
        return attrs


class ParcelQuoteRequestSerializer(ParcelLocationInputSerializer):
    pass


class ParcelCreateSerializer(ParcelLocationInputSerializer):
    payment_method = serializers.ChoiceField(choices=ParcelShipment.PaymentMethod.choices)


class ParcelStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ParcelStatusHistory
        fields = ("status", "note", "created_at")
        read_only_fields = fields


class ParcelShipmentSerializer(serializers.ModelSerializer):
    status_history = ParcelStatusHistorySerializer(many=True, read_only=True)
    sender_name = serializers.SerializerMethodField()
    driver_name = serializers.SerializerMethodField()

    class Meta:
        model = ParcelShipment
        fields = (
            "id", "package_size", "package_description", "recipient_name", "recipient_phone",
            "pickup_address", "pickup_latitude", "pickup_longitude",
            "destination_address", "destination_latitude", "destination_longitude",
            "estimated_distance_km", "quoted_fare", "currency", "status",
            "payment_method", "payment_status", "sender_name", "driver", "driver_name",
            "requested_at", "assigned_at", "picked_up_at", "in_transit_at", "delivered_at",
            "cancelled_at", "proof_note", "status_history", "created_at", "updated_at",
        )
        read_only_fields = fields

    def get_sender_name(self, obj):
        return obj.sender.get_full_name().strip() or obj.sender.email

    def get_driver_name(self, obj):
        if obj.driver is None:
            return None
        return obj.driver.get_full_name().strip() or obj.driver.email


class ParcelDriverStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=(
        (ParcelShipment.Status.PICKED_UP, "Picked up"),
        (ParcelShipment.Status.IN_TRANSIT, "In transit"),
        (ParcelShipment.Status.DELIVERED, "Delivered"),
    ))
    delivery_code = serializers.CharField(required=False, allow_blank=False, max_length=12, write_only=True)
    proof_note = serializers.CharField(required=False, allow_blank=True, max_length=255, trim_whitespace=True)

    def validate(self, attrs):
        if attrs["status"] == ParcelShipment.Status.DELIVERED and not attrs.get("delivery_code"):
            raise serializers.ValidationError({"delivery_code": "A delivery confirmation code is required."})
        return attrs


class ParcelCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255, trim_whitespace=True)
