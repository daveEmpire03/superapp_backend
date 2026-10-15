from django.db import models
from core.models import TimeStampedModel
from apps.orders.models import Order
class Payment(TimeStampedModel):
    class Status(models.TextChoices): INITIALIZED="INITIALIZED","Initialized"; SUCCESS="SUCCESS","Success"; FAILED="FAILED","Failed"; REFUNDED="REFUNDED","Refunded"
    order=models.ForeignKey(Order,on_delete=models.PROTECT,related_name="payments")
    provider=models.CharField(max_length=30,default="FLUTTERWAVE")
    tx_ref=models.CharField(max_length=120,unique=True)
    provider_transaction_id=models.CharField(max_length=120,blank=True)
    amount=models.DecimalField(max_digits=12,decimal_places=2)
    currency=models.CharField(max_length=3,default="NGN")
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.INITIALIZED)
    raw_response=models.JSONField(default=dict,blank=True)


class ServicePayment(TimeStampedModel):
    """Payment for non-grocery services such as passenger rides and parcels."""

    class Status(models.TextChoices):
        INITIALIZED = "INITIALIZED", "Initialized"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    class ServiceType(models.TextChoices):
        RIDE = "RIDE", "Passenger ride"
        PARCEL = "PARCEL", "Parcel shipment"

    user = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="service_payments"
    )
    service_type = models.CharField(max_length=12, choices=ServiceType.choices)
    ride = models.ForeignKey(
        "rides.Ride", on_delete=models.PROTECT, null=True, blank=True,
        related_name="service_payments",
    )
    parcel = models.ForeignKey(
        "parcels.ParcelShipment", on_delete=models.PROTECT, null=True, blank=True,
        related_name="service_payments",
    )
    provider = models.CharField(max_length=30, default="FLUTTERWAVE")
    tx_ref = models.CharField(max_length=120, unique=True)
    provider_transaction_id = models.CharField(max_length=120, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIALIZED)
    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(service_type="RIDE", ride__isnull=False, parcel__isnull=True)
                    | models.Q(service_type="PARCEL", parcel__isnull=False, ride__isnull=True)
                ),
                name="service_payment_one_target",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "status"], name="service_pay_user_status_idx"),
        ]

    def __str__(self):
        return f"{self.tx_ref} - {self.service_type} - {self.status}"
