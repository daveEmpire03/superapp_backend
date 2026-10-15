import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import TimeStampedModel


class ParcelShipment(TimeStampedModel):
    class PackageSize(models.TextChoices):
        DOCUMENT = "DOCUMENT", "Document"
        SMALL = "SMALL", "Small"
        MEDIUM = "MEDIUM", "Medium"
        LARGE = "LARGE", "Large"

    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        DRIVER_ASSIGNED = "DRIVER_ASSIGNED", "Driver assigned"
        PICKED_UP = "PICKED_UP", "Picked up"
        IN_TRANSIT = "IN_TRANSIT", "In transit"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"
        NO_DRIVER = "NO_DRIVER", "No driver available"

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        ONLINE = "ONLINE", "Online"

    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="parcel_shipments"
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_parcels", limit_choices_to={"role": "RIDER"},
    )
    package_size = models.CharField(max_length=12, choices=PackageSize.choices)
    package_description = models.CharField(max_length=500)
    recipient_name = models.CharField(max_length=150)
    recipient_phone = models.CharField(max_length=20)
    pickup_address = models.CharField(max_length=255)
    pickup_latitude = models.DecimalField(max_digits=10, decimal_places=7, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    pickup_longitude = models.DecimalField(max_digits=10, decimal_places=7, validators=[MinValueValidator(-180), MaxValueValidator(180)])
    destination_address = models.CharField(max_length=255)
    destination_latitude = models.DecimalField(max_digits=10, decimal_places=7, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    destination_longitude = models.DecimalField(max_digits=10, decimal_places=7, validators=[MinValueValidator(-180), MaxValueValidator(180)])
    estimated_distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    quoted_fare = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED, db_index=True)
    payment_method = models.CharField(max_length=8, choices=PaymentMethod.choices)
    payment_status = models.CharField(max_length=12, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID, db_index=True)
    delivery_code_hash = models.CharField(max_length=256)
    requested_at = models.DateTimeField(auto_now_add=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    in_transit_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    proof_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sender", "status"], name="parcel_sender_status_idx"),
            models.Index(fields=["driver", "status"], name="parcel_driver_status_idx"),
            models.Index(fields=["status", "created_at"], name="parcel_status_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(quoted_fare__gte=0), name="parcel_fare_nonnegative"),
        ]

    def __str__(self):
        return f"{self.pk} - {self.get_status_display()}"


class ParcelStatusHistory(TimeStampedModel):
    parcel = models.ForeignKey(ParcelShipment, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=20, choices=ParcelShipment.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="parcel_status_changes",
    )
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["parcel", "created_at"], name="parcel_history_created_idx")]

    def __str__(self):
        return f"{self.parcel_id} - {self.status}"
