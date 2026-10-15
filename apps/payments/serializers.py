from rest_framework import serializers


class InitializePaymentSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    redirect_url = serializers.URLField()


class VerifyPaymentSerializer(serializers.Serializer):
    transaction_id = serializers.CharField(
        max_length=120,
        trim_whitespace=True,
    )

    def validate_transaction_id(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Transaction ID is required.")

        return value


class InitializeServicePaymentSerializer(serializers.Serializer):
    service_type = serializers.ChoiceField(choices=(("RIDE", "Passenger ride"), ("PARCEL", "Parcel shipment")))
    service_id = serializers.UUIDField()
    redirect_url = serializers.URLField()


class VerifyServicePaymentSerializer(serializers.Serializer):
    transaction_id = serializers.CharField(max_length=120, trim_whitespace=True)

    def validate_transaction_id(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Transaction ID is required.")
        return value
