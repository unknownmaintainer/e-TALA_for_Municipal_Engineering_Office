"""
Management command: seed_requirement_templates

Populates RequirementTemplate and RequirementItem tables with structured document checklists
for Building Permits, Municipal Projects, and Barangay Projects according to Municipal Engineering Office workflow.

Run after migration:
    python manage.py seed_requirement_templates
"""
from django.core.management.base import BaseCommand
from permits.models import RequirementTemplate, RequirementItem


TEMPLATES = [
    # ── 1. Building Permit ───────────────────────────────────────────────────
    {
        'record_type': 'Permit',
        'subtype': 'Building',
        'scope': '',
        'items': [
            {
                'name': 'Building Permit with Attached Ancillary Permits',
                'desc': 'Unified Office of the Building Official (OBO) Ancillary Permit Forms.',
                'sub_items': [
                    ('Architectural Permit', 'Architectural Permit form signed and sealed by registered Architect.'),
                    ('Civil / Structural Permit', 'Civil/Structural Permit form signed and sealed by Civil/Structural Engineer.'),
                    ('Electrical Permit', 'Electrical Permit form signed and sealed by Professional Electrical Engineer (PEE).'),
                    ('Plumbing and Sanitary Permit', 'Plumbing & Sanitary Permit form signed and sealed by Master Plumber / Sanitary Engineer.'),
                    ('Fencing Permit', 'Fencing Permit form signed and sealed by Civil Engineer / Architect.'),
                    ('Mechanical Permit', 'Mechanical Permit form signed and sealed by Professional Mechanical Engineer (PME).'),
                    ('Electronics Permit', 'Electronics Permit form signed and sealed by Professional Electronics Engineer (PECE).'),
                ]
            },
            {'name': 'Barangay Clearance', 'desc': 'Barangay Clearance from the respective barangay where the structure will be constructed.', 'sub_items': []},
            {'name': 'Certified True Copy of OCT / TCT (Registry of Deeds)', 'desc': 'Certified true copy of land title on file with the Registry of Deeds.', 'sub_items': []},
            {'name': 'Tax Declaration', 'desc': 'Certified true copy of current Tax Declaration.', 'sub_items': []},
            {'name': 'Current Real Property Tax Receipt', 'desc': 'Official Receipt of current Real Property Tax (RPT) payment.', 'sub_items': []},
            {'name': 'Notarized Copy of Contract of Lease or Deed of Absolute Sale', 'desc': 'Required if the applicant is not the registered owner of the lot.', 'sub_items': []},
            {'name': 'Sketch Plan of the Land with Technical Description', 'desc': 'Geodetic Engineer lot sketch plan showing technical descriptions, boundaries, and landmarks.', 'sub_items': []},
            {'name': 'Zoning Clearance', 'desc': 'Zoning Clearance issued by MPDO / Zoning Administrator.', 'sub_items': []},
            {'name': 'Locational Clearance', 'desc': 'Locational Clearance from the Municipal Planning & Development Office.', 'sub_items': []},
            {
                'name': 'Building Plans',
                'desc': 'Complete architectural, structural, and engineering drawing sets.',
                'sub_items': [
                    ('Site Development Plan', 'Site Development Plan, Vicinity Map, and Zoning Lot Details.'),
                    ('Architectural Plan', 'Floor plans, elevations, sections, schedules of doors & windows.'),
                    ('Structural Plan', 'Foundation plan, framing plans, slab/beam/column schedules and structural details.'),
                    ('Electrical Plan', 'Lighting & power layouts, single line diagram, riser diagram, load schedule.'),
                    ('Plumbing and Sanitary Plan', 'Water distribution, sewer drainage, septic tank / STP detail.'),
                    ('Electronics Plan', 'Telecom, LAN, CCTV, cable TV, and aux layouts.'),
                    ('Mechanical Plan', 'HVAC, ducting, ventilation, equipment layouts (if applicable).'),
                    ('Fire Protection Plan', 'Fire sprinkler system, standpipe, emergency exits, FDAS drawings.'),
                ]
            },
            {'name': 'Project Estimated Cost', 'desc': 'Itemized Bill of Materials (BOM) and Cost Estimates signed and sealed by Engineer/Architect.', 'sub_items': []},
            {'name': 'Specifications', 'desc': 'Written architectural and engineering technical specifications signed and sealed.', 'sub_items': []},
        ],
    },

    # ── 2. Certificate of Occupancy ──────────────────────────────────────────
    {
        'record_type': 'Permit',
        'subtype': 'Occupancy',
        'scope': '',
        'items': [
            {
                'name': 'Certificate of Occupancy with Attached Documents',
                'desc': 'Occupancy certificate application and mandatory completion clearances.',
                'sub_items': [
                    ('Application Form for Certificate of Occupancy', 'Duly accomplished Occupancy Permit Application Form.'),
                    ('Certificate of Completion', 'Signed & sealed Certificate of Completion by Architect/Civil Engineer in-charge.'),
                    ('As-Built Plan', 'Complete set of signed & sealed As-Built architectural, structural, electrical, and plumbing drawings.'),
                    ('FSIC (Fire Safety Inspection Certificate)', 'Fire Safety Inspection Certificate issued by Bureau of Fire Protection (BFP).'),
                ]
            }
        ],
    },

    # ── 3. Fencing Permit ────────────────────────────────────────────────────
    {
        'record_type': 'Permit',
        'subtype': 'Fencing',
        'scope': '',
        'items': [
            {
                'name': 'Fencing Permit with Attached Documents',
                'desc': 'Unified Fencing Permit Form and mandatory supporting clearances/drawings.',
                'sub_items': [
                    ('Fencing Permit Application Form', 'Unified Fencing Permit Form signed and sealed.'),
                    ('Barangay Clearance', 'Barangay Clearance certifying site clearance for fencing.'),
                    ('Certified True Copy of OCT / TCT (Registry of Deeds)', 'Certified copy of land title on file with Registry of Deeds.'),
                    ('Tax Declaration', 'Current Tax Declaration copy.'),
                    ('Current Real Property Tax Receipt', 'Current Real Property Tax official receipt.'),
                    ('Notarized Copy of Contract of Lease or Deed of Absolute Sale', 'Required if the applicant is not the registered owner of the lot.'),
                    ('Sketch Plan of the Land with Technical Description', 'Sketch plan with technical description certified by Geodetic Engineer.'),
                    ('Zoning Clearance', 'Zoning Clearance issued by MPDO.'),
                    ('Fencing Plan', 'Signed & sealed fencing layout and elevation drawings with boundary lines.'),
                    ('Project Cost Estimate and Specifications', 'Itemized cost estimate and technical specifications for fencing.'),
                ]
            }
        ],
    },

    # ── 4. Electrical Permit ─────────────────────────────────────────────────
    {
        'record_type': 'Permit',
        'subtype': 'Electrical',
        'scope': '',
        'items': [
            {
                'name': 'Electrical Permit with Attached Documents',
                'desc': 'Unified Electrical Permit application, clearances, house photo, and electrical plan.',
                'sub_items': [
                    ('Electrical Permit Application Form', 'Unified Electrical Permit Form signed & sealed by PEE/REE/RME.'),
                    ('Barangay Clearance', 'Barangay Clearance certifying electrical installation clearance.'),
                    ('Certified True Copy of OCT / TCT (Registry of Deeds)', 'Certified copy of land title on file with Registry of Deeds.'),
                    ('Tax Declaration', 'Current Tax Declaration copy.'),
                    ('Current Real Property Tax Receipt', 'Current Real Property Tax official receipt.'),
                    ('Notarized Copy of Contract of Lease or Deed of Absolute Sale', 'Required if the applicant is not the registered owner of the lot.'),
                    ('3R Size House Picture', '3R size clear photograph of the house/structure showing the proposed service entrance location.'),
                    ('Electrical Plan', 'Electrical wiring layout, service entrance detail, and load schedule.'),
                    ('Fire Safety Evaluation Clearance', 'Fire Safety Evaluation Clearance (FSEC) issued by Bureau of Fire Protection (BFP).'),
                ]
            }
        ],
    },

    # ── 5. Municipal Projects (5 Core Required Documents) ────────────────────
    {
        'record_type': 'Project',
        'subtype': 'Roads and Bridges',
        'scope': 'Municipal',
        'items': [
            {'name': 'Building Plans', 'desc': 'Complete architectural, civil, structural, and infrastructure engineering plans.', 'sub_items': []},
            {'name': 'Program of Works', 'desc': 'Official LGU Program of Works (POW) and financial cost estimates.', 'sub_items': []},
            {'name': 'Statement of Work Accomplished', 'desc': 'Statement of Work Accomplished (SWA) and progress accomplishment reports.', 'sub_items': []},
            {'name': 'Inspection Report', 'desc': 'Engineering QA/QC inspection reports, site monitoring, and material test results.', 'sub_items': []},
            {'name': 'Certificate of Completion', 'desc': 'Certificate of Project Completion and Final Acceptance signed by Municipal Engineer.', 'sub_items': []},
        ],
    },

    # ── 6. Barangay Projects (3 Core Required Documents) ─────────────────────
    {
        'record_type': 'Project',
        'subtype': 'Roads and Bridges',
        'scope': 'Barangay',
        'items': [
            {'name': 'Building Plans', 'desc': 'Project plans and layout drawings.', 'sub_items': []},
            {'name': 'Program of Works', 'desc': 'Official Barangay / Municipal Program of Works (POW) and budget.', 'sub_items': []},
            {'name': 'Inspection Report', 'desc': 'Site inspection report and monitoring report by Municipal Engineering Office.', 'sub_items': []},
        ],
    },
]

# Generate templates for the 4 official project types:
#   'Roads and Bridges', 'Vertical Structures', 'Flood Control and Drainage System', 'Potable Water System'
PROJECT_TYPES_ALL = [
    'Vertical Structures',
    'Flood Control and Drainage System',
    'Potable Water System',
]

muni_base = TEMPLATES[4]  # Municipal 'Roads and Bridges' (5 core documents)
brgy_base = TEMPLATES[5]  # Barangay 'Roads and Bridges' (3 core documents)

for ptype in PROJECT_TYPES_ALL:
    t_muni = dict(muni_base)
    t_muni['subtype'] = ptype
    t_muni['scope'] = 'Municipal'
    TEMPLATES.append(t_muni)

    t_brgy = dict(brgy_base)
    t_brgy['subtype'] = ptype
    t_brgy['scope'] = 'Barangay'
    TEMPLATES.append(t_brgy)


class Command(BaseCommand):
    help = 'Seeds RequirementTemplate and RequirementItem tables with structured document checklists.'

    def handle(self, *args, **options):
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

            active_item_ids = []

            for order, item_data in enumerate(t_data['items'], start=1):
                has_subs = bool(item_data.get('sub_items'))
                parent_item, i_created = RequirementItem.objects.update_or_create(
                    template=template,
                    name=item_data['name'],
                    defaults={
                        'description': item_data['desc'],
                        'parent': None,
                        'order': order,
                        'is_active': True,
                        'is_group': has_subs
                    },
                )
                active_item_ids.append(parent_item.pk)
                if i_created:
                    created_items += 1

                # Create sub items
                for sub_order, (sub_name, sub_desc) in enumerate(item_data.get('sub_items', []), start=1):
                    sub_item, sub_created = RequirementItem.objects.update_or_create(
                        template=template,
                        name=sub_name,
                        defaults={
                            'description': sub_desc,
                            'parent': parent_item,
                            'order': sub_order,
                            'is_active': True,
                            'is_group': False
                        },
                    )
                    active_item_ids.append(sub_item.pk)
                    if sub_created:
                        created_items += 1

            # Deactivate items belonging to this template that are no longer part of the template
            obsolete_items = RequirementItem.objects.filter(template=template).exclude(pk__in=active_item_ids)
            for obs in obsolete_items:
                # If unused in any record requirements, safely delete; otherwise mark inactive
                if not obs.record_requirements.exists() and not obs.documents.exists():
                    obs.delete()
                else:
                    obs.is_active = False
                    obs.save(update_fields=['is_active'])

        self.stdout.write(self.style.SUCCESS(
            f'Successfully seeded {created_templates} requirement templates and {created_items} items/sub-items.'
        ))
