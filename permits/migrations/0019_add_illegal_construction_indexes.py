# Generated for eTala performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('permits', '0018_document_permits_doc_expiry__0ff11d_idx_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='engineeringrecord',
            index=models.Index(fields=['is_illegal_construction'], name='permits_eng_is_ille_idx'),
        ),
        migrations.AddIndex(
            model_name='engineeringrecord',
            index=models.Index(fields=['illegal_compliance_status'], name='permits_eng_illega_comp_idx'),
        ),
    ]
