from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('permits', '0019_add_illegal_construction_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='barangay',
            name='psgc_code',
            field=models.CharField(
                blank=True,
                help_text='Official PSA PSGC 10-digit Code (e.g. 0803715001)',
                max_length=20,
                null=True,
                unique=True
            ),
        ),
    ]
