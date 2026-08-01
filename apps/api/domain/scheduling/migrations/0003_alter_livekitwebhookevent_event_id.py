from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0002_academiceventparticipant_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='livekitwebhookevent',
            name='event_id',
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
