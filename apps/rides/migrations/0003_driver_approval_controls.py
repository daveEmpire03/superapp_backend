from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rides", "0002_ride_driver_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="ridedriverprofile",
            name="is_approved",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="ridedriverprofile",
            name="is_suspended",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
