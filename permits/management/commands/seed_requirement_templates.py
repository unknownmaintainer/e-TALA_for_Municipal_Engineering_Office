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
                    ('Architectural Permit Form (a.1)', 'Architectural Permit form signed and sealed by registered Architect.'),
                    ('Civil / Structural Permit Form (a.2)', 'Civil/Structural Permit form signed and sealed by Civil/Structural Engineer.'),
                    ('Electrical Permit Form (a.3)', 'Electrical Permit form signed and sealed by Professional Electrical Engineer (PEE).'),
                    ('Plumbing and Sanitary Permit Form (a.4)', 'Plumbing & Sanitary Permit form signed and sealed by Master Plumber / Sanitary Engineer.'),
                    ('Fencing Permit Form (a.5)', 'Fencing Permit form signed and sealed by Civil Engineer / Architect.'),
                    ('Mechanical Permit Form (a.6)', 'Mechanical Permit form signed and sealed by Professional Mechanical Engineer (PME).'),
                    ('Electronics Permit Form (a.7)', 'Electronics Permit form signed and sealed by Professional Electronics Engineer (PECE).'),
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
                'name': 'Building Plans (Signed & Sealed)',
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
                    ('Application Form for Certificate of Occupancy (a.1)', 'Duly accomplished Occupancy Permit Application Form.'),
                    ('Certificate of Completion (a.2)', 'Signed & sealed Certificate of Completion by Architect/Civil Engineer in-charge.'),
                    ('As-Built Plan (a.3)', 'Complete set of signed & sealed As-Built architectural, structural, electrical, and plumbing drawings.'),
                    ('FSIC - Fire Safety Inspection Certificate (a.4)', 'Fire Safety Inspection Certificate issued by Bureau of Fire Protection (BFP).'),
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
                'desc': 'Unified Fencing Permit Form signed and sealed.',
                'sub_items': [
                    ('Fencing Permit Application Form', 'Unified Fencing Permit Form signed and sealed.'),
                    ('Fencing Plan', 'Signed & sealed fencing layout and elevation drawings with boundary lines.'),
                    ('Project Cost Estimate and Specifications', 'Itemized cost estimate and technical specifications for fencing.'),
                ]
            },
            {'name': 'Barangay Clearance', 'desc': 'Barangay Clearance certifying site clearance for fencing.', 'sub_items': []},
            {'name': 'Certified True Copy of OCT / TCT (Registry of Deeds)', 'desc': 'Certified copy of land title on file with Registry of Deeds.', 'sub_items': []},
            {'name': 'Tax Declaration', 'desc': 'Current Tax Declaration copy.', 'sub_items': []},
            {'name': 'Current Real Property Tax Receipt', 'desc': 'Current Real Property Tax official receipt.', 'sub_items': []},
            {'name': 'Notarized Copy of Contract of Lease or Deed of Absolute Sale', 'desc': 'Required if the applicant is not the registered owner of the lot.', 'sub_items': []},
            {'name': 'Sketch Plan of the Land with Technical Description', 'desc': 'Sketch plan with technical description certified by Geodetic Engineer.', 'sub_items': []},
            {'name': 'Zoning Clearance', 'desc': 'Zoning Clearance issued by MPDO.', 'sub_items': []},
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
                'desc': 'Electrical permit application and engineering drawings.',
                'sub_items': [
                    ('Electrical Permit Application Form', 'Unified Electrical Permit Form signed & sealed by PEE.'),
                    ('Electrical Single Line Diagram & Load Schedule', 'Single line diagram, load computation, and riser diagram certified by PEE.'),
                    ('Electrical Layout & Power Plan', 'Lighting, power, and emergency power layouts.'),
                ]
            },
            {'name': 'Barangay Clearance', 'desc': 'Barangay Clearance certifying electrical installation clearance.', 'sub_items': []},
            {'name': 'Certified True Copy of OCT / TCT (Registry of Deeds)', 'desc': 'Certified copy of land title on file with Registry of Deeds.', 'sub_items': []},
            {'name': 'Tax Declaration', 'desc': 'Current Tax Declaration.', 'sub_items': []},
            {'name': 'Current Real Property Tax Receipt', 'desc': 'Current Real Property Tax official receipt.', 'sub_items': []},
            {'name': 'Notarized Copy of Contract of Lease or Deed of Absolute Sale', 'desc': 'Required if the applicant is not the registered owner of the lot.', 'sub_items': []},
            {'name': '3R Size House Picture', 'desc': '3R size clear photograph of the house/structure showing the proposed service entrance location.', 'sub_items': []},
            {'name': 'Fire Safety Evaluation Clearance (FSEC)', 'desc': 'FSEC certificate issued by Bureau of Fire Protection (BFP).', 'sub_items': []},
        ],
    },

    # ── 5. Municipal Projects (5 Core Required Documents) ────────────────────
    {
        'record_type': 'Project',
        'subtype': 'Road & Bridge',
        'scope': 'Municipal',
        'items': [
            {
                'name': 'Building Plans',
                'desc': 'Complete architectural, civil, structural, and infrastructure engineering plans.',
                'sub_items': [
                    ('Plan and Profile Drawings', 'Alignment plan and longitudinal profile drawings.'),
                    ('Cross Section Plans', 'Detailed roadway/structure cross sections.'),
                    ('Drainage & Culvert Details', 'Drainage structure and cross-drain detail drawings.'),
                ]
            },
            {
                'name': 'Program of Works (POW)',
                'desc': 'Official LGU Program of Work and financial cost estimates.',
                'sub_items': [
                    ('Approved Program of Work (POW)', 'Official POW form detailing itemized scope and unit costs.'),
                    ('Detailed Quantity Take-off & Cost Estimate', 'Itemized cost estimate breakdown.'),
                    ('Approved Budget for the Contract (ABC)', 'Signed ABC document.'),
                ]
            },
            {'name': 'Statement of Work Accomplished (SWA)', 'desc': 'Periodic Statement of Work Accomplished / billing accomplishment reports.', 'sub_items': []},
            {'name': 'Inspection Report', 'desc': 'Engineering QA/QC inspection reports, site monitoring, and material test results.', 'sub_items': []},
            {'name': 'Certificate of Completion', 'desc': 'Certificate of Project Completion and Final Acceptance signed by Municipal Engineer.', 'sub_items': []},
        ],
    },

    # ── 6. Barangay Projects (3 Core Required Documents) ─────────────────────
    {
        'record_type': 'Project',
        'subtype': 'Road & Bridge',
        'scope': 'Barangay',
        'items': [
            {
                'name': 'Building Plans',
                'desc': 'Project plans and layout drawings.',
                'sub_items': [
                    ('Engineering Plans / Layout Drawings', 'Project drawings and layout details.'),
                    ('Cross Section / Detail Drawings', 'Structural and site detail drawings.'),
                ]
            },
            {
                'name': 'Program of Works (POW)',
                'desc': 'Official Barangay / Municipal Program of Work.',
                'sub_items': [
                    ('Approved Program of Work (POW)', 'Official POW detailing project scope and budget.'),
                    ('Bill of Materials & Cost Estimate', 'Itemized material take-off and unit cost estimate.'),
                ]
            },
            {'name': 'Inspection Report', 'desc': 'Site inspection report and monitoring report by Municipal Engineering Office.', 'sub_items': []},
        ],
    },
]

# Generate templates for all project types matching ProjectDetail.PROJECT_TYPE_CHOICES
# These are the actual values stored in the DB:
#   'Road & Bridge', 'Vertical Structure', 'Flood Control', 'Potable Water',
#   'Building', 'Water System', 'Drainage', 'Multi-purpose Hall', 'Others'
PROJECT_TYPES_ALL = [
    'Vertical Structure',
    'Flood Control',
    'Potable Water',
    'Building',
    'Water System',
    'Drainage',
    'Multi-purpose Hall',
    'Others',
]

muni_base = TEMPLATES[4]  # Municipal 'Road & Bridge' (5 core documents)
brgy_base = TEMPLATES[5]  # Barangay 'Road & Bridge' (3 core documents)

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

            for order, item_data in enumerate(t_data['items'], start=1):
                has_subs = bool(item_data.get('sub_items'))
                parent_item, i_created = RequirementItem.objects.update_or_create(
                    template=template,
                    name=item_data['name'],
                    parent=None,
                    defaults={'description': item_data['desc'], 'order': order, 'is_active': True, 'is_group': has_subs},
                )
                if i_created:
                    created_items += 1

                # Create sub items
                for sub_order, (sub_name, sub_desc) in enumerate(item_data.get('sub_items', []), start=1):
                    _, sub_created = RequirementItem.objects.update_or_create(
                        template=template,
                        name=sub_name,
                        parent=parent_item,
                        defaults={'description': sub_desc, 'order': sub_order, 'is_active': True, 'is_group': False},
                    )
                    if sub_created:
                        created_items += 1

        self.stdout.write(self.style.SUCCESS(
            f'Successfully seeded {created_templates} requirement templates and {created_items} items/sub-items.'
        ))
