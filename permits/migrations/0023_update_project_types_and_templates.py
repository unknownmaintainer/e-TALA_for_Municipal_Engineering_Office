# Generated for eTala Municipal Engineering Office
import django.db.models.deletion
from django.db import migrations, models

def update_project_types_and_templates(apps, schema_editor):
    ProjectDetail = apps.get_model('permits', 'ProjectDetail')
    RequirementTemplate = apps.get_model('permits', 'RequirementTemplate')
    RequirementItem = apps.get_model('permits', 'RequirementItem')
    RecordRequirement = apps.get_model('permits', 'RecordRequirement')
    EngineeringRecord = apps.get_model('permits', 'EngineeringRecord')

    # 1. Normalize existing ProjectDetail records
    type_mapping = {
        'Road & Bridge': 'Roads and Bridges',
        'Road and Bridge': 'Roads and Bridges',
        'Roads & Bridges': 'Roads and Bridges',
        'Vertical Structure': 'Vertical Structures',
        'Building': 'Vertical Structures',
        'Multi-purpose Hall': 'Vertical Structures',
        'Multi-Purpose Building': 'Vertical Structures',
        'Flood Control': 'Flood Control and Drainage System',
        'Drainage': 'Flood Control and Drainage System',
        'Drainage & Sewerage': 'Flood Control and Drainage System',
        'Potable Water': 'Potable Water System',
        'Water System': 'Potable Water System',
        'Others': 'Roads and Bridges',
    }

    for pd in ProjectDetail.objects.all():
        if pd.project_type in type_mapping:
            pd.project_type = type_mapping[pd.project_type]
            pd.save(update_fields=['project_type'])

    # 2. Update requirement templates for all 4 project types (Municipal & Barangay)
    project_subtypes = [
        'Roads and Bridges',
        'Vertical Structures',
        'Flood Control and Drainage System',
        'Potable Water System',
    ]

    official_items = [
        ('Building Plans', 'Complete architectural, civil, structural, and infrastructure engineering plans.', 1),
        ('Program of Works', 'Official LGU Program of Works (POW) and financial cost estimates.', 2),
        ('Statement of Work Accomplished', 'Statement of Work Accomplished (SWA) and progress accomplishment reports.', 3),
        ('Inspection Report', 'Engineering QA/QC inspection reports, site monitoring, and material test results.', 4),
        ('Certificate of Completion', 'Certificate of Project Completion and Final Acceptance signed by Municipal Engineer.', 5),
    ]

    for scope in ['Municipal', 'Barangay']:
        for subtype in project_subtypes:
            template, _ = RequirementTemplate.objects.get_or_create(
                record_type='Project',
                subtype=subtype,
                scope=scope,
                defaults={'is_active': True}
            )

            # Create or update the 5 flat items
            item_objs = []
            for name, desc, order in official_items:
                # Find existing or create
                item = RequirementItem.objects.filter(template=template, name__iexact=name).first()
                if not item:
                    # Also check for previous variations like 'Program of Works (POW)' or 'Statement of Work Accomplished (SWA)'
                    if 'Program of Works' in name:
                        item = RequirementItem.objects.filter(template=template, name__icontains='Program of Works').first()
                    elif 'Statement of Work Accomplished' in name:
                        item = RequirementItem.objects.filter(template=template, name__icontains='Statement of Work Accomplished').first()
                    elif 'Building Plans' in name:
                        item = RequirementItem.objects.filter(template=template, name__icontains='Building Plans').first()

                if item:
                    item.name = name
                    item.description = desc
                    item.order = order
                    item.parent = None
                    item.is_group = False
                    item.is_active = True
                    item.save()
                else:
                    item = RequirementItem.objects.create(
                        template=template,
                        name=name,
                        description=desc,
                        order=order,
                        parent=None,
                        is_group=False,
                        is_active=True
                    )
                item_objs.append(item)

            # Clean up old nested sub-items for this template
            RequirementItem.objects.filter(template=template).exclude(
                pk__in=[it.pk for it in item_objs]
            ).delete()

    # 3. Synchronize RecordRequirement for all existing project records
    for rec in EngineeringRecord.objects.filter(record_type='Project'):
        scope = rec.project_scope or 'Municipal'
        subtype = 'Roads and Bridges'
        try:
            if hasattr(rec, 'project_detail') and rec.project_detail and rec.project_detail.project_type:
                subtype = rec.project_detail.project_type
        except Exception:
            pass

        template = RequirementTemplate.objects.filter(record_type='Project', subtype=subtype, scope=scope, is_active=True).first()
        if not template:
            template = RequirementTemplate.objects.filter(record_type='Project', scope=scope, is_active=True).first()
        if not template:
            template = RequirementTemplate.objects.filter(record_type='Project', is_active=True).first()

        if template:
            target_items = list(RequirementItem.objects.filter(template=template, is_active=True).order_by('order'))
            for item in target_items:
                RecordRequirement.objects.get_or_create(record=rec, requirement_item=item)
            # Clean up any old obsolete sub-item requirements
            RecordRequirement.objects.filter(record=rec).exclude(requirement_item__in=target_items).delete()


def rollback_project_types(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('permits', '0022_userdevice_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectdetail',
            name='project_type',
            field=models.CharField(
                choices=[
                    ('Roads and Bridges', 'Roads and Bridges'),
                    ('Vertical Structures', 'Vertical Structures'),
                    ('Flood Control and Drainage System', 'Flood Control and Drainage System'),
                    ('Potable Water System', 'Potable Water System'),
                ],
                max_length=50,
            ),
        ),
        migrations.RunPython(update_project_types_and_templates, rollback_project_types),
    ]
