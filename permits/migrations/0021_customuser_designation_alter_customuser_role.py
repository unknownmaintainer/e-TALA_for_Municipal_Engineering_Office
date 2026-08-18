from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('permits', '0020_barangay_psgc_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='designation',
            field=models.CharField(
                blank=True,
                default='',
                max_length=150,
                verbose_name='Job Title / Designation'
            ),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(
                choices=[
                    ('admin', 'Engineering Office Head (Admin)'),
                    ('staff', 'Engineering Staff')
                ],
                default='staff',
                max_length=20
            ),
        ),
    ]
