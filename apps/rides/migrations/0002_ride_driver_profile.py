# Adds dispatch-specific driver vehicle, availability, and location data.
import django.core.validators
import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rides", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RideDriverProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("vehicle_type", models.CharField(choices=[("CAR", "Car"), ("MOTORCYCLE", "Motorcycle")], max_length=16)),
                ("vehicle_plate", models.CharField(max_length=20)),
                ("vehicle_make", models.CharField(blank=True, max_length=80)),
                ("vehicle_color", models.CharField(blank=True, max_length=40)),
                ("is_available", models.BooleanField(db_index=True, default=False)),
                ("current_latitude", models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(-90), django.core.validators.MaxValueValidator(90)])),
                ("current_longitude", models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)])),
                ("last_location_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.OneToOneField(limit_choices_to={"role": "RIDER"}, on_delete=django.db.models.deletion.CASCADE, related_name="ride_driver_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name="ridedriverprofile",
            index=models.Index(fields=["vehicle_type", "is_available"], name="ride_driver_vehicle_avail_idx"),
        ),
    ]
