from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("volunteers", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="volunteerprofile",
            name="address_line1",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="volunteerprofile",
            name="city",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="volunteerprofile",
            name="country",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="volunteerprofile",
            name="geo_latitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name="volunteerprofile",
            name="geo_longitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name="volunteerprofile",
            name="postal_code",
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
