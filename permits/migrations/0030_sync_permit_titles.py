from django.db import migrations

def sync_permit_titles(apps, schema_editor):
    EngineeringRecord = apps.get_model('permits', 'EngineeringRecord')
    PermitDetail = apps.get_model('permits', 'PermitDetail')
    
    # Sync regular permits where title doesn't match applicant_name / permit_number
    permits = EngineeringRecord.objects.filter(record_type='Permit', is_illegal_construction=False)
    for rec in permits:
        try:
            pd = PermitDetail.objects.filter(engineering_record=rec).first()
            if pd and (pd.applicant_name or pd.permit_number):
                new_title = f"{pd.permit_number} — {pd.applicant_name}" if pd.permit_number and pd.applicant_name else (pd.applicant_name or pd.permit_number)
                if new_title and rec.title != new_title:
                    rec.title = new_title
                    rec.save(update_fields=['title'])
        except Exception:
            pass

class Migration(migrations.Migration):
    dependencies = [
        ('permits', '0029_recordaccesslog_and_more'),
    ]
    operations = [
        migrations.RunPython(sync_permit_titles, reverse_code=migrations.RunPython.noop),
    ]
