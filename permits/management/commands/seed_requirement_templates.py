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
            {'name': 'Barangay Clearance for Building Construction', 'desc': 'Barangay Clearance certifying site clearance.', 'sub_items': []},
            {'name': 'Certified True Copy of OCT/TCT (Registry of Deeds)', 'desc': 'Certified copy of land title on file with Registry of Deeds.', 'sub_items': []},
            {'name': 'Current Tax Declaration & Real Property Tax Receipt', 'desc': 'Certified true copy of current Tax Declaration & RPT Receipt.', 'sub_items': []},
            {'name': 'Notarized Contract of Lease or Deed of Absolute Sale', 'desc': 'Notarized lease contract or Deed of Sale (if applicant is not registered lot owner).', 'sub_items': []},
            {'name': 'Sketch Plan of Land with Technical Description', 'desc': 'Geodetic Engineer lot sketch plan with technical description.', 'sub_items': []},
            {
                'name': 'Ancillary Permit Forms',
                'desc': 'Unified Office of the Building Official (OBO) Ancillary Permit Forms.',
                'sub_items': [
                    ('Architectural Permit Form (Unified Form 1)', 'Architectural Permit form signed and sealed by registered Architect.'),
                    ('Civil/Structural Permit Form (Unified Form 2)', 'Civil/Structural Permit form signed and sealed by Civil/Structural Engineer.'),
                    ('Electrical Permit Form (Unified Form 3)', 'Electrical Permit form signed and sealed by Professional Electrical Engineer (PEE).'),
                    ('Plumbing & Sanitary Permit Form (Unified Form 4)', 'Plumbing & Sanitary Permit form signed and sealed by Master Plumber/Sanitary Engineer.'),
                    ('Mechanical Permit Form (Unified Form 5)', 'Mechanical Permit form signed and sealed by Professional Mechanical Engineer (PME).'),
                    ('Electronics Permit Form (Unified Form 6)', 'Electronics Permit form signed and sealed by Professional Electronics Engineer (PECE).'),
                ]
            },
            {
                'name': 'Building Plans (5 Sets Signed & Sealed)',
                'desc': 'Complete architectural, structural, and engineering drawing sets.',
                'sub_items': [
                    ('Site Development & Location Plan', 'Site Development Plan, Vicinity Map, Zoning Lot Details.'),
                    ('Architectural Plans', 'Architectural floor plans, elevations, sections, schedules of doors & windows.'),
                    ('Structural Plans', 'Foundation plan, roof framing, structural slab & column details, schedules.'),
                    ('Electrical Plans', 'Lighting & power layouts, single line diagram, riser diagram, load schedule.'),
                    ('Plumbing & Sanitary Plans', 'Water distribution system, waste drainage system, septic tank detail.'),
                    ('Mechanical Plans', 'HVAC, ducting, ventilation, equipment layouts (if applicable).'),
                    ('Electronics Plans', 'Telecom, LAN, CCTV, cable TV, FDAS layout drawings (if applicable).'),
                ]
            },
            {
                'name': 'Structural & Geotechnical Documents',
                'desc': 'Structural engineering analysis, calculations, and soil test reports.',
                'sub_items': [
                    ('Structural Analysis & Design Computation', 'Signed & sealed by Structural Engineer (required for structures 2 storeys & above).'),
                    ('Soil Test / Geotechnical Investigation Report', 'Signed & sealed Geotechnical Engineer report (required for 3 storeys & above).'),
                    ('Seismic & Wind Load Computations', 'Structural seismic, dead load, and lateral wind load computations.'),
                ]
            },
            {
                'name': 'Project Cost Estimates & Technical Specifications',
                'desc': 'Detailed bill of materials and architectural/engineering specifications.',
                'sub_items': [
                    ('Itemized Bill of Materials (BOM) & Cost Estimate', 'Detailed itemized cost computation signed & sealed by Engineer/Architect.'),
                    ('Written Technical Specifications', 'Technical material specifications signed & sealed by Engineer/Architect.'),
                ]
            },
            {
                'name': 'Environmental & Special Clearances',
                'desc': 'Official clearances from government agencies and municipal offices.',
                'sub_items': [
                    ('Fire Safety Evaluation Clearance (FSEC)', 'FSEC clearance certificate issued by Bureau of Fire Protection (BFP).'),
                    ('Locational & Zoning Clearance', 'Zoning clearance certificate issued by Municipal Planning & Dev. Office (MPDO).'),
                    ('Environmental Compliance Certificate (ECC) / CNC', 'DENR-EMB clearance certificate (for commercial/industrial/multi-dwelling).'),
                ]
            },
        ],
    },

    # ── 2. Certificate of Occupancy ──────────────────────────────────────────
    {
        'record_type': 'Permit',
        'subtype': 'Occupancy',
        'scope': '',
        'items': [
            {
                'name': 'Certificate of Occupancy Attachments',
                'desc': 'Occupancy certificate inspection and completion attachments folder.',
                'sub_items': [
                    ('Application Form for Certificate of Occupancy', 'Duly accomplished Occupancy Permit Application Form.'),
                    ('Certificate of Completion (Signed & Sealed)', 'Completion certificate signed & sealed by Architect/Engineer in-charge.'),
                    ('Complete As-Built Engineering Plans', 'Signed & sealed As-Built architectural, structural, electrical, and plumbing drawings.'),
                    ('FSIC for Occupancy (BFP Clearance)', 'Fire Safety Inspection Certificate issued by Bureau of Fire Protection.'),
                    ('Construction Logbook', 'Signed & sealed logbook of daily site inspections.'),
                    ('Building Inspection Photographs', 'Photos of completed building exterior (front, sides, rear) and interior.'),
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
            {'name': 'Barangay Clearance', 'desc': 'Barangay Clearance certifying site clearance.', 'sub_items': []},
            {'name': 'Certified True Copy of OCT/TCT', 'desc': 'Certified copy of land title.', 'sub_items': []},
            {'name': 'Current Tax Declaration & RPT Receipt', 'desc': 'Current Tax Declaration & RPT Receipt.', 'sub_items': []},
            {'name': 'Notarized Contract of Lease or Deed of Sale', 'desc': 'Lease or Deed of Sale (if applicant is not lot owner).', 'sub_items': []},
            {'name': 'Sketch Plan of Land with Technical Description', 'desc': 'Lot sketch plan with technical description.', 'sub_items': []},
            {'name': 'Zoning Clearance', 'desc': 'Zoning Clearance from MPDO.', 'sub_items': []},
            {
                'name': 'Fencing Requirements & Drawings',
                'desc': 'Fencing plans and cost estimate folder.',
                'sub_items': [
                    ('Fencing Permit Application Form', 'Unified Fencing Permit Form.'),
                    ('Fencing Plan & Boundary Layout', 'Signed & sealed fencing plan drawing showing lot boundary.'),
                    ('Fencing Cost Estimate & Bill of Materials', 'Itemized cost estimate for fencing construction.'),
                ]
            },
        ],
    },

    # ── 4. Electrical Permit ─────────────────────────────────────────────────
    {
        'record_type': 'Permit',
        'subtype': 'Electrical',
        'scope': '',
        'items': [
            {
                'name': 'Electrical Documents & Ancillary Attachments',
                'desc': 'Electrical permit application and engineering computation folder.',
                'sub_items': [
                    ('Electrical Permit Application Form', 'Unified Electrical Permit Application Form.'),
                    ('Electrical Single Line Diagram', 'Electrical Single Line Diagram certified by PEE.'),
                    ('Electrical Layout & Power Plan', 'Lighting and power outlet layout drawings.'),
                    ('Electrical Load Schedule & Computations', 'Detailed load analysis, voltage drop, and short circuit calculations.'),
                    ('3R Size House / Structure Photo', '3R size photo of house or structure showing service entrance.'),
                    ('Fire Safety Evaluation Clearance (FSEC)', 'FSEC clearance issued by Bureau of Fire Protection (BFP).'),
                ]
            },
            {'name': 'Barangay Clearance', 'desc': 'Barangay Clearance.', 'sub_items': []},
            {'name': 'Certified True Copy of OCT/TCT', 'desc': 'Certified copy of land title.', 'sub_items': []},
            {'name': 'Current Tax Declaration & RPT Receipt', 'desc': 'Current Tax Declaration & RPT Receipt.', 'sub_items': []},
            {'name': 'Notarized Contract of Lease or Deed of Sale', 'desc': 'Lease or Deed of Sale (if applicant is not lot owner).', 'sub_items': []},
        ],
    },

    # ── 5. Municipal Projects ────────────────────────────────────────────────
    {
        'record_type': 'Project',
        'subtype': 'Road & Bridge',
        'scope': 'Municipal',
        'items': [
            {
                'name': 'Engineering Plans & Project Drawings',
                'desc': 'Complete DPWH/Municipal engineering drawing set.',
                'sub_items': [
                    ('Plan and Profile Drawings', 'Alignment plan and longitudinal profile drawings.'),
                    ('Cross Section Plans', 'Detailed roadway/bridge cross sections.'),
                    ('Drainage & Culvert Details', 'Drainage structure and cross-drain detail drawings.'),
                ]
            },
            {
                'name': 'Program of Works (POW) & Budget Estimates',
                'desc': 'Official LGU Program of Work and financial estimates.',
                'sub_items': [
                    ('Approved Program of Work (POW)', 'Official POW form detailing itemized scope and unit costs.'),
                    ('Detailed Quantity Take-off & Cost Estimate', 'Itemized cost estimate spreadsheet.'),
                    ('Approved Budget for the Contract (ABC)', 'Signed ABC document.'),
                ]
            },
            {'name': 'Statement of Work Accomplished (SWA)', 'desc': 'Periodic Statement of Work Accomplished.', 'sub_items': []},
            {'name': 'Engineering Inspection Reports', 'desc': 'Periodic site inspection & QA/QC test reports.', 'sub_items': []},
            {'name': 'Certificate of Project Completion & Final Acceptance', 'desc': 'Certificate of Project Completion & Acceptance.', 'sub_items': []},
        ],
    },
]

# Duplicate municipal project checklist structure for all Municipal & Barangay project types
MUNICIPAL_PROJECT_TYPES = ['Vertical Structure', 'Flood Control', 'Potable Water', 'Building', 'Water System', 'Drainage', 'Multi-purpose Hall', 'Others']
BARANGAY_PROJECT_TYPES = ['Road & Bridge', 'Vertical Structure', 'Flood Control', 'Potable Water', 'Building', 'Water System', 'Drainage', 'Multi-purpose Hall', 'Others']

muni_template = TEMPLATES[4]
for ptype in MUNICIPAL_PROJECT_TYPES:
    t_copy = dict(muni_template)
    t_copy['subtype'] = ptype
    t_copy['scope'] = 'Municipal'
    TEMPLATES.append(t_copy)

for ptype in BARANGAY_PROJECT_TYPES:
    t_copy = dict(muni_template)
    t_copy['subtype'] = ptype
    t_copy['scope'] = 'Barangay'
    TEMPLATES.append(t_copy)


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
