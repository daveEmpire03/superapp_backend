import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("rides", "0003_driver_approval_controls"),
    ]

    operations = [
        migrations.CreateModel(
            name="ParcelShipment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("package_size", models.CharField(choices=[("DOCUMENT", "Document"), ("SMALL", "Small"), ("MEDIUM", "Medium"), ("LARGE", "Large")], max_length=12)),
                ("package_description", models.CharField(max_length=500)),
                ("recipient_name", models.CharField(max_length=150)),
                ("recipient_phone", models.CharField(max_length=20)),
                ("pickup_address", models.CharField(max_length=255)),
                ("pickup_latitude", models.DecimalField(decimal_places=7, max_digits=10, validators=[django.core.validators.MinValueValidator(-90), django.core.validators.MaxValueValidator(90)])),
                ("pickup_longitude", models.DecimalField(decimal_places=7, max_digits=10, validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)])),
                ("destination_address", models.CharField(max_length=255)),
                ("destination_latitude", models.DecimalField(decimal_places=7, max_digits=10, validators=[django.core.validators.MinValueValidator(-90), django.core.validators.MaxValueValidator(90)])),
                ("destination_longitude", models.DecimalField(decimal_places=7, max_digits=10, validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)])),
                ("estimated_distance_km", models.DecimalField(decimal_places=2, max_digits=8)),
                ("quoted_fare", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="NGN", max_length=3)),
                ("status", models.CharField(choices=[("REQUESTED", "Requested"), ("DRIVER_ASSIGNED", "Driver assigned"), ("PICKED_UP", "Picked up"), ("IN_TRANSIT", "In transit"), ("DELIVERED", "Delivered"), ("CANCELLED", "Cancelled"), ("NO_DRIVER", "No driver available")], db_index=True, default="REQUESTED", max_length=20)),
                ("payment_method", models.CharField(choices=[("CASH", "Cash"), ("ONLINE", "Online")], max_length=8)),
                ("payment_status", models.CharField(choices=[("UNPAID", "Unpaid"), ("PENDING", "Pending"), ("PAID", "Paid"), ("FAILED", "Failed"), ("REFUNDED", "Refunded")], db_index=True, default="UNPAID", max_length=12)),
                ("delivery_code_hash", models.CharField(max_length=256)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("assigned_at", models.DateTimeField(blank=True, null=True)),
                ("picked_up_at", models.DateTimeField(blank=True, null=True)),
                ("in_transit_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("proof_note", models.CharField(blank=True, max_length=255)),
                ("driver", models.ForeignKey(blank=True, limit_choices_to={"role": "RIDER"}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_parcels", to=settings.AUTH_USER_MODEL)),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="parcel_shipments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="parcelshipment", index=models.Index(fields=["sender", "status"], name="parcel_sender_status_idx")),
        migrations.AddIndex(model_name="parcelshipment", index=models.Index(fields=["driver", "status"], name="parcel_driver_status_idx")),
        migrations.AddIndex(model_name="parcelshipment", index=models.Index(fields=["status", "created_at"], name="parcel_status_created_idx")),
        migrations.AddConstraint(model_name="parcelshipment", constraint=models.CheckConstraint(condition=models.Q(("quoted_fare__gte", 0)), name="parcel_fare_nonnegative")),
        migrations.CreateModel(
            name="ParcelStatusHistory",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(choices=[("REQUESTED", "Requested"), ("DRIVER_ASSIGNED", "Driver assigned"), ("PICKED_UP", "Picked up"), ("IN_TRANSIT", "In transit"), ("DELIVERED", "Delivered"), ("CANCELLED", "Cancelled"), ("NO_DRIVER", "No driver available")], max_length=20)),
                ("note", models.CharField(blank=True, max_length=255)),
                ("changed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="parcel_status_changes", to=settings.AUTH_USER_MODEL)),
                ("parcel", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="status_history", to="parcels.parcelshipment")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddIndex(model_name="parcelstatushistory", index=models.Index(fields=["parcel", "created_at"], name="parcel_history_created_idx")),
    ]
