from rest_framework import serializers

from .models import AnalyticsEvent


class AnalyticsEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsEvent

        fields = (
            "id",
            "name",
            "properties",
            "created_at",
        )

        read_only_fields = (
            "id",
            "created_at",
        )

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Event name is required.")

        return value


class AnalyticsPeriodQuerySerializer(serializers.Serializer):
    start_date = serializers.DateField(
        required=False,
    )

    end_date = serializers.DateField(
        required=False,
    )

    store_id = serializers.UUIDField(
        required=False,
    )

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if start_date is not None and end_date is not None and start_date > end_date:
            raise serializers.ValidationError(
                {"end_date": ("End date cannot be earlier " "than start date.")}
            )

        if (
            start_date is not None
            and end_date is not None
            and (end_date - start_date).days > 366
        ):
            raise serializers.ValidationError(
                {"date_range": ("Analytics date range cannot " "exceed 366 days.")}
            )

        return attrs


class AnalyticsStoreQuerySerializer(serializers.Serializer):
    store_id = serializers.UUIDField(
        required=False,
    )
