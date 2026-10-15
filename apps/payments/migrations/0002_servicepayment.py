import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_initial"),
        ("rides", "0003_driver_approval_controls"),
        ("parcels", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ServicePayment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("service_type", models.CharField(choices=[("RIDE", "Passenger ride"), ("PARCEL", "Parcel shipment")], max_length=12)),
                ("provider", models.CharField(default="FLUTTERWAVE", max_length=30)),
                ("tx_ref", models.CharField(max_length=120, unique=True)),
                ("provider_transaction_id", models.CharField(blank=True, max_length=120)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="NGN", max_length=3)),
                ("status", models.CharField(choices=[("INITIALIZED", "Initialized"), ("SUCCESS", "Success"), ("FAILED", "Failed"), ("REFUNDED", "Refunded")], default="INITIALIZED", max_length=20)),
                ("raw_response", models.JSONField(blank=True, default=dict)),
                ("parcel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="service_payments", to="parcels.parcelshipment")),
                ("ride", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="service_payments", to="rides.ride")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="service_payments", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="servicepayment",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(service_type="RIDE", ride__isnull=False, parcel__isnull=True)
                    | models.Q(service_type="PARCEL", parcel__isnull=False, ride__isnull=True)
                ),
                name="service_payment_one_target",
            ),
        ),
        migrations.AddIndex(
            model_name="servicepayment",
            index=models.Index(fields=["user", "status"], name="service_pay_user_status_idx"),
        ),
    ]
