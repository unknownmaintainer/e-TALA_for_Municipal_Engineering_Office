# Generated for 60-day trash auto-retention policy

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('permits', '0026_rename_permits_eng_is_ille_idx_permits_eng_is_ille_33d7d1_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='engineeringrecord',
            name='deleted_at',
            field=models.DateTimeField(blank=True, db_index=True, help_text='Timestamp when moved to trash / archived for 60-day auto-retention tracking.', null=True),
        ),
        migrations.AddIndex(
            model_name='engineeringrecord',
            index=models.Index(fields=['status', 'deleted_at'], name='permits_eng_status_deleted_idx'),
        ),
    ]
