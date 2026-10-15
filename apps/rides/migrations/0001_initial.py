# Generated for the initial passenger ride domain.
import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Ride",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("vehicle_type", models.CharField(choices=[("CAR", "Car"), ("MOTORCYCLE", "Motorcycle")], max_length=16)),
                ("status", models.CharField(choices=[("REQUESTED", "Requested"), ("SEARCHING", "Searching for driver"), ("DRIVER_ASSIGNED", "Driver assigned"), ("DRIVER_ARRIVING", "Driver arriving"), ("IN_PROGRESS", "In progress"), ("COMPLETED", "Completed"), ("CANCELLED", "Cancelled"), ("NO_DRIVER", "No driver available")], db_index=True, default="REQUESTED", max_length=24)),
                ("pickup_address", models.CharField(max_length=255)),
                ("pickup_latitude", models.DecimalField(decimal_places=7, max_digits=10, validators=[django.core.validators.MinValueValidator(-90), django.core.validators.MaxValueValidator(90)])),
                ("pickup_longitude", models.DecimalField(decimal_places=7, max_digits=10, validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)])),
                ("destination_address", models.CharField(max_length=255)),
                ("destination_latitude", models.DecimalField(decimal_places=7, max_digits=10, validators=[django.core.validators.MinValueValidator(-90), django.core.validators.MaxValueValidator(90)])),
                ("destination_longitude", models.DecimalField(decimal_places=7, max_digits=10, validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)])),
                ("quoted_fare", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="NGN", max_length=3)),
                ("payment_method", models.CharField(choices=[("CASH", "Cash"), ("ONLINE", "Online")], max_length=8)),
                ("payment_status", models.CharField(choices=[("UNPAID", "Unpaid"), ("PENDING", "Pending"), ("PAID", "Paid"), ("FAILED", "Failed"), ("REFUNDED", "Refunded")], db_index=True, default="UNPAID", max_length=12)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("driver_assigned_at", models.DateTimeField(blank=True, null=True)),
                ("trip_started_at", models.DateTimeField(blank=True, null=True)),
                ("trip_completed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("passenger_note", models.TextField(blank=True)),
                ("driver", models.ForeignKey(blank=True, limit_choices_to={"role": "RIDER"}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="driven_rides", to=settings.AUTH_USER_MODEL)),
                ("passenger", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="passenger_rides", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="ride", index=models.Index(fields=["passenger", "status"], name="ride_passenger_status_idx")),
        migrations.AddIndex(model_name="ride", index=models.Index(fields=["driver", "status"], name="ride_driver_status_idx")),
        migrations.AddIndex(model_name="ride", index=models.Index(fields=["status", "created_at"], name="ride_status_created_idx")),
        migrations.AddConstraint(model_name="ride", constraint=models.CheckConstraint(condition=models.Q(("quoted_fare__gte", 0)), name="ride_quoted_fare_nonnegative")),
        migrations.CreateModel(
            name="RideStatusHistory",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(choices=[("REQUESTED", "Requested"), ("SEARCHING", "Searching for driver"), ("DRIVER_ASSIGNED", "Driver assigned"), ("DRIVER_ARRIVING", "Driver arriving"), ("IN_PROGRESS", "In progress"), ("COMPLETED", "Completed"), ("CANCELLED", "Cancelled"), ("NO_DRIVER", "No driver available")], max_length=24)),
                ("note", models.CharField(blank=True, max_length=255)),
                ("changed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ride_status_changes", to=settings.AUTH_USER_MODEL)),
                ("ride", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="status_history", to="rides.ride")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddIndex(model_name="ridestatushistory", index=models.Index(fields=["ride", "created_at"], name="ride_history_created_idx")),
    ]
