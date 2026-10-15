from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import TimeStampedModel


class Ride(TimeStampedModel):
    """A passenger trip, intentionally independent from grocery Orders/Delivery."""

    class VehicleType(models.TextChoices):
        CAR = "CAR", "Car"
        MOTORCYCLE = "MOTORCYCLE", "Motorcycle"

    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        SEARCHING = "SEARCHING", "Searching for driver"
        DRIVER_ASSIGNED = "DRIVER_ASSIGNED", "Driver assigned"
        DRIVER_ARRIVING = "DRIVER_ARRIVING", "Driver arriving"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"
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

    passenger = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="passenger_rides",
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="driven_rides",
        limit_choices_to={"role": "RIDER"},
    )

    vehicle_type = models.CharField(max_length=16, choices=VehicleType.choices)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )

    pickup_address = models.CharField(max_length=255)
    pickup_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    pickup_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    destination_address = models.CharField(max_length=255)
    destination_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    destination_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )

    # Snapshot of the quoted amount; later pricing changes must not alter a trip.
    quoted_fare = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    payment_method = models.CharField(max_length=8, choices=PaymentMethod.choices)
    payment_status = models.CharField(
        max_length=12,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
        db_index=True,
    )

    requested_at = models.DateTimeField(auto_now_add=True)
    driver_assigned_at = models.DateTimeField(null=True, blank=True)
    trip_started_at = models.DateTimeField(null=True, blank=True)
    trip_completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    passenger_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["passenger", "status"], name="ride_passenger_status_idx"),
            models.Index(fields=["driver", "status"], name="ride_driver_status_idx"),
            models.Index(fields=["status", "created_at"], name="ride_status_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quoted_fare__gte=0),
                name="ride_quoted_fare_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.pk} - {self.get_status_display()}"


class RideStatusHistory(TimeStampedModel):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=24, choices=Ride.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ride_status_changes",
    )
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["ride", "created_at"], name="ride_history_created_idx"),
        ]

    def __str__(self):
        return f"{self.ride_id} - {self.status}"
