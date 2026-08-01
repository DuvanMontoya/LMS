from django.db import migrations


def seed_platform_registration_settings(apps, schema_editor):
    del schema_editor
    registration_settings = apps.get_model("identity", "PlatformRegistrationSettings")
    registration_settings.objects.get_or_create(singleton=1)


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0002_platformregistrationsettings"),
    ]

    operations = [
        migrations.RunPython(
            seed_platform_registration_settings,
            migrations.RunPython.noop,
        ),
    ]
