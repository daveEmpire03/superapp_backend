from rest_framework import serializers

from apps.accounts.models import User

from .models import (
    Delivery,
    DeliveryStatusHistory,
)


class DeliveryStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryStatusHistory

        fields = [
            "id",
            "status",
            "changed_by",
            "changed_by_name",
            "note",
            "created_at",
        ]

        read_only_fields = fields

    def get_changed_by_name(self, obj):
        if not obj.changed_by:
            return None

        return obj.changed_by.get_full_name() or obj.changed_by.username


class DeliverySerializer(serializers.ModelSerializer):
    order_reference = serializers.CharField(
        source="order.reference",
        read_only=True,
    )

    order_status = serializers.CharField(
        source="order.status",
        read_only=True,
    )

    store_id = serializers.UUIDField(
        source="order.store_id",
        read_only=True,
    )

    store_name = serializers.CharField(
        source="order.store.name",
        read_only=True,
    )

    customer_name = serializers.SerializerMethodField()

    rider_name = serializers.SerializerMethodField()

    history = DeliveryStatusHistorySerializer(
        source="status_history",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Delivery

        fields = [
            "id",
            "order",
            "order_reference",
            "order_status",
            "store_id",
            "store_name",
            "customer_name",
            "rider",
            "rider_name",
            "status",
            "assigned_at",
            "accepted_at",
            "picked_up_at",
            "out_for_delivery_at",
            "delivered_at",
            "cancelled_at",
            "delivery_note",
            "proof_note",
            "history",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields

    def get_customer_name(self, obj):
        return obj.order.user.get_full_name() or obj.order.user.username

    def get_rider_name(self, obj):
        if not obj.rider:
            return None

        return obj.rider.get_full_name() or obj.rider.username


class AssignRiderSerializer(serializers.Serializer):
    rider_id = serializers.UUIDField()

    def validate_rider_id(self, value):
        try:
            rider = User.objects.get(
                id=value,
                role=User.Role.RIDER,
                is_active=True,
            )

        except User.DoesNotExist:
            raise serializers.ValidationError("Active rider not found.")

        self.context["rider"] = rider

        return value


class RiderDeliveryStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            Delivery.Status.ACCEPTED,
            Delivery.Status.PICKED_UP,
            Delivery.Status.OUT_FOR_DELIVERY,
            Delivery.Status.DELIVERED,
            Delivery.Status.REJECTED,
        ]
    )

    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )

    proof_note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )


class StaffDeliveryCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )
