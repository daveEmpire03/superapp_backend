from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="category",
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.AlterModelOptions(
            name="product",
            options={"ordering": ["name"]},
        ),
    ]
