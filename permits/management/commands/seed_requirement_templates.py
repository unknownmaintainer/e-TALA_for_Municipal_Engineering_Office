"""
Management command: seed_requirement_templates

Populates RequirementTemplate and RequirementItem tables with all
document checklists for the three record categories:
  - Permit Records (Building, Occupancy, Electrical, Fencing)
  - Municipal Projects (Road & Bridge, Vertical Structure, Flood Control, Potable Water)
  - Barangay Projects (Road & Bridge, Vertical Structure, Flood Control, Potable Water)

Run once after migration:
    python manage.py seed_requirement_templates

Safe to re-run: uses get_or_create so it won't duplicate data.
"""
from django.core.management.base import BaseCommand
from permits.models import RequirementTemplate, RequirementItem


TEMPLATES = [
    # ── Permit Records ────────────────────────────────────────────────────────
    {
        'record_type': 'Permit',
        'subtype': 'Building',
        'scope': '',
        'items': [
            ('Building Permit with attached ancillary permits', 'Main building permit application form and ancillary permits.'),
            ('Architectural Permit', 'Ancillary Permit: Architectural Permit form and layout plans.'),
            ('Civil/Structural Permit', 'Ancillary Permit: Civil/Structural Permit form and plans.'),
            ('Electrical Permit', 'Ancillary Permit: Electrical Permit form and plans.'),
            ('Plumbing and Sanitary Permit', 'Ancillary Permit: Plumbing and Sanitary Permit form and plans.'),
            ('Fencing Permit', 'Ancillary Permit: Fencing Permit form and plans.'),
            ('Mechanical Permit', 'Ancillary Permit: Mechanical Permit form and plans.'),
            ('Electronics Permit', 'Ancillary Permit: Electronics Permit form and plans.'),
            ('Barangay Clearance', 'Barangay Clearance certifying project site clearance.'),
            ('Certified True copy of OCT/TCT, on file with the Registry of Deeds', 'Certified True copy of OCT/TCT, on file with the Registry of Deeds.'),
            ('Tax Declaration', 'Certified true copy of the current Tax Declaration of the property.'),
            ('Current Real Property Tax Receipt', 'Receipt showing payment of current Real Property Tax.'),
            ('Notarized copy of Contract of Lease or Deed of Absolute Sale, If in case the applicant is not the registered owner of the lot', 'Notarized copy of Contract of Lease or Deed of Absolute Sale (if applicant is not the registered owner).'),
            ('Sketch Plan of the land with Technical Description', 'Land sketch plan including its technical description.'),
            ('Zoning Clearance', 'Zoning clearance certificate from MPDO.'),
            ('Locational Clearance', 'Locational clearance certifying compliance with zoning ordinance.'),
            ("Building Plans (Site Dev't. Plan, Architectural Plan, Structural Plan, Electrical Plan, Plumbing and Sanitary Plan, Electronics, Mechanical Plan, Fire Protection Plan)", 'Complete Building Plans including Site Development, Architectural, Structural, Electrical, Plumbing/Sanitary, Electronics, Mechanical, and Fire Protection.'),
            ('Project Estimated Cost', 'Detailed bill of materials and estimated cost of the construction.'),
            ('Specifications', 'Technical specifications describing materials and construction quality.'),
        ],
    },
    {
        'record_type': 'Permit',
        'subtype': 'Occupancy',
        'scope': '',
        'items': [
            ('Certificate of Occupancy with attached Documents', 'Main Certificate of Occupancy document and attachments.'),
            ('Application Form', 'Certificate of Occupancy Application Form.'),
            ('Certificate of Completion', 'Certificate of Completion signed by the in-charge engineer/architect.'),
            ('As-Built Plan', 'As-Built Plan representing the finalized building layout.'),
            ('FSIC (Fire Safety Inspection Certificate)', 'Fire Safety Inspection Certificate from the Bureau of Fire Protection (BFP).'),
        ],
    },
    {
        'record_type': 'Permit',
        'subtype': 'Electrical',
        'scope': '',
        'items': [
            ('Electrical Permit with attached Documents', 'Main Electrical Permit application document and attachments.'),
            ('Barangay Clearance', 'Barangay Clearance certifying project site clearance.'),
            ('Certified True copy of OCT/TCT, on file with the Registry of Deeds', 'Certified True copy of OCT/TCT, on file with the Registry of Deeds.'),
            ('Tax Declaration', 'Certified true copy of the current Tax Declaration of the property.'),
            ('Current Real Property Tax Receipt', 'Receipt showing payment of current Real Property Tax.'),
            ('Notarized copy of Contract of Lease or Deed of Absolute Sale, If in case the applicant is not the registered owner of the lot', 'Notarized copy of Contract of Lease or Deed of Absolute Sale (if applicant is not the registered owner).'),
            ('3R size House Picture', '3R size photo of the house/structure.'),
            ('Fire Safety Evaluation Clearance', 'Fire Safety Evaluation Clearance from the Bureau of Fire Protection (BFP).'),
        ],
    },
    {
        'record_type': 'Permit',
        'subtype': 'Fencing',
        'scope': '',
        'items': [
            ('Fencing Permit with attached Documents', 'Main Fencing Permit application document and attachments.'),
            ('Barangay Clearance', 'Barangay Clearance certifying project site clearance.'),
            ('Certified True copy of OCT/TCT, on file with the Registry of Deeds', 'Certified True copy of OCT/TCT, on file with the Registry of Deeds.'),
            ('Tax Declaration', 'Certified true copy of the current Tax Declaration of the property.'),
            ('Current Real Property Tax Receipt', 'Receipt showing payment of current Real Property Tax.'),
            ('Notarized copy of Contract of Lease or Deed of Absolute Sale, If in case the applicant is not the registered owner of the lot', 'Notarized copy of Contract of Lease or Deed of Absolute Sale (if applicant is not the registered owner).'),
            ('Sketch Plan of the land with Technical Description', 'Land sketch plan including its technical description.'),
            ('Zoning Clearance', 'Zoning clearance certificate from MPDO.'),
            ('Fencing Plan', 'Fencing plan layout showing boundaries and details.'),
            ('Project Cost Estimate and Specifications', 'Project cost estimate and technical specifications for fencing construction.'),
        ],
    },

    # ── Municipal Projects ────────────────────────────────────────────────────
    {
        'record_type': 'Project',
        'subtype': 'Road & Bridge',
        'scope': 'Municipal',
        'items': [
            ('Building Plans', 'Complete building plans or engineering drawings for the project.'),
            ('Program of Works', 'Program of Works detailing activities, quantities, unit costs, and schedule.'),
            ('SWA', 'Sworn Warranties and Affidavits from the contractor and project engineer.'),
            ('Inspection Report', 'Official inspection report from the Municipal Engineering Office.'),
            ('Certificate of Completion', 'Certificate of Completion confirming project completion.'),
        ],
    },
    {
        'record_type': 'Project',
        'subtype': 'Vertical Structure',
        'scope': 'Municipal',
        'items': [
            ('Building Plans', 'Complete building plans or engineering drawings for the project.'),
            ('Program of Works', 'Program of Works detailing activities, quantities, unit costs, and schedule.'),
            ('SWA', 'Sworn Warranties and Affidavits from the contractor and project engineer.'),
            ('Inspection Report', 'Official inspection report from the Municipal Engineering Office.'),
            ('Certificate of Completion', 'Certificate of Completion confirming project completion.'),
        ],
    },
    {
        'record_type': 'Project',
        'subtype': 'Flood Control',
        'scope': 'Municipal',
        'items': [
            ('Building Plans', 'Complete building plans or engineering drawings for the project.'),
            ('Program of Works', 'Program of Works detailing activities, quantities, unit costs, and schedule.'),
            ('SWA', 'Sworn Warranties and Affidavits from the contractor and project engineer.'),
            ('Inspection Report', 'Official inspection report from the Municipal Engineering Office.'),
            ('Certificate of Completion', 'Certificate of Completion confirming project completion.'),
        ],
    },
    {
        'record_type': 'Project',
        'subtype': 'Potable Water',
        'scope': 'Municipal',
        'items': [
            ('Building Plans', 'Complete building plans or engineering drawings for the project.'),
            ('Program of Works', 'Program of Works detailing activities, quantities, unit costs, and schedule.'),
            ('SWA', 'Sworn Warranties and Affidavits from the contractor and project engineer.'),
            ('Inspection Report', 'Official inspection report from the Municipal Engineering Office.'),
            ('Certificate of Completion', 'Certificate of Completion confirming project completion.'),
        ],
    },

    # ── Barangay Projects ─────────────────────────────────────────────────────
    {
        'record_type': 'Project',
        'subtype': 'Road & Bridge',
        'scope': 'Barangay',
        'items': [
            ('Building Plans', 'Building plans or engineering drawings for the project.'),
            ('Program of Works', 'Program of Works detailing activities, quantities, unit costs, and schedule.'),
            ('Inspection Report', 'Official inspection report from the Municipal Engineering Office.'),
        ],
    },
    {
        'record_type': 'Project',
        'subtype': 'Vertical Structure',
        'scope': 'Barangay',
        'items': [
            ('Building Plans', 'Building plans or engineering drawings for the project.'),
            ('Program of Works', 'Program of Works detailing activities, quantities, unit costs, and schedule.'),
            ('Inspection Report', 'Official inspection report from the Municipal Engineering Office.'),
        ],
    },
    {
        'record_type': 'Project',
        'subtype': 'Flood Control',
        'scope': 'Barangay',
        'items': [
            ('Building Plans', 'Building plans or engineering drawings for the project.'),
            ('Program of Works', 'Program of Works detailing activities, quantities, unit costs, and schedule.'),
            ('Inspection Report', 'Official inspection report from the Municipal Engineering Office.'),
        ],
    },
    {
        'record_type': 'Project',
        'subtype': 'Potable Water',
        'scope': 'Barangay',
        'items': [
            ('Building Plans', 'Building plans or engineering drawings for the project.'),
            ('Program of Works', 'Program of Works detailing activities, quantities, unit costs, and schedule.'),
            ('Inspection Report', 'Official inspection report from the Municipal Engineering Office.'),
        ],
    },
]


class Command(BaseCommand):
    help = 'Seeds RequirementTemplate and RequirementItem tables with all document checklists.'

    def handle(self, *args, **options):
        # 1. Rename old names to new names to preserve existing files and prevent warnings
        rename_map = {
            'Electrical Permit Application Form': 'Electrical Permit with attached Documents',
            'Certified True Copy of Land Title or Tax Declaration': 'Certified True copy of OCT/TCT, on file with the Registry of Deeds',
            'Tax Clearance Certificate': 'Current Real Property Tax Receipt',
            'Building Plans / Engineering Drawings': 'Building Plans',
            'Program of Works (POW)': 'Program of Works',
            'Sworn Warranties and Affidavits (SWA)': 'SWA',
            'Building Plans / Architectural and Structural Drawings': 'Building Plans',
        }

        for old_name, new_name in rename_map.items():
            items_to_rename = RequirementItem.objects.filter(name=old_name)
            for item in items_to_rename:
                if not RequirementItem.objects.filter(template=item.template, name=new_name).exists():
                    self.stdout.write(f'  Renaming "{old_name}" -> "{new_name}" for template {item.template}')
                    item.name = new_name
                    item.save()

        created_templates = 0
        created_items = 0

        for t_data in TEMPLATES:
            template, t_created = RequirementTemplate.objects.get_or_create(
                record_type=t_data['record_type'],
                subtype=t_data['subtype'],
                scope=t_data['scope'],
            )
            if t_created:
                created_templates += 1
                self.stdout.write(f'  Created template: {template}')
            else:
                self.stdout.write(f'  Existing template: {template}')

            # Get new item names
            new_item_names = [item_info[0] for item_info in t_data['items']]

            # Delete old items that are no longer in the checklist and not referenced
            existing_items = RequirementItem.objects.filter(template=template)
            for item in existing_items:
                if item.name not in new_item_names:
                    if not item.record_requirements.exists():
                        self.stdout.write(f'    Deleting old unused item: {item.name}')
                        item.delete()
                    else:
                        self.stdout.write(f'    Item in use, marking as inactive: {item.name}')
                        item.is_active = False
                        item.save()

            # Create or update items
            for order, (name, description) in enumerate(t_data['items'], start=1):
                item, i_created = RequirementItem.objects.update_or_create(
                    template=template,
                    name=name,
                    defaults={'description': description, 'order': order, 'is_active': True},
                )
                if i_created:
                    created_items += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Created {created_templates} templates and {created_items} requirement items.'
        ))
