from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("senior_care", "0003_dailyactivity"),
    ]

    operations = [
        migrations.AddField(
            model_name="seniorprofile",
            name="pair_code",
            field=models.CharField(blank=True, max_length=6),
        ),
        migrations.AddField(
            model_name="seniorprofile",
            name="is_connected",
            field=models.BooleanField(default=False),
        ),
    ]
