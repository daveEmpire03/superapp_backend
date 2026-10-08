from rest_framework import serializers

from .models import (
    DeviceToken,
    Notification,
)


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken

        fields = (
            "id",
            "token",
            "platform",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification

        fields = (
            "id",
            "notification_type",
            "title",
            "message",
            "data",
            "is_read",
            "read_at",
            "created_at",
        )

        read_only_fields = fields
