from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rides", "0003_driver_approval_controls"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ridedriverprofile",
            name="vehicle_plate",
            field=models.CharField(max_length=20, unique=True),
        ),
    ]
