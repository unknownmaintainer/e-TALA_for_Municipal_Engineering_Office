"""
Management command: seed_demo_records

Seeds realistic, professional demo records for the Municipal Engineering Office (Carigara, Leyte):
- 5 Realistic Permits (Building, Occupancy, Electrical, Fencing)
- 5 Realistic Infrastructure Projects (Roads & Bridges, Vertical Structures, Flood Control, Water System)
- 5 Illegal Constructions (Diverse statuses: resolved vs unresolved, varying years, different barangays)
- 5 Trash / Soft-deleted Records (Varying retention days left, e.g. 28d, 22d, 15d, 7d, 3d)

All records can be safely edited, deleted, restored, or permanently deleted by staff during live demos.
"""
import os
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone
from permits.models import (
    CustomUser, Barangay, EngineeringRecord, PermitDetail, ProjectDetail,
    RequirementTemplate, RecordRequirement, Document, AuditLog
)

# Minimal valid PDF binary content for testing and demo uploads
DUMMY_PDF_BYTES = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n"


SAMPLE_PERMITS = [
    {
        'title': '#BP-2026-0142 — Dr. Elena S. Mendoza',
        'permit_number': 'BP-2026-0142',
        'applicant_name': 'Dr. Elena S. Mendoza',
        'permit_type': 'Building',
        'building_type': 'Commercial',
        'barangay_name': 'Jugaban (Poblacion)',
        'year': 2026,
        'date_issued': date(2026, 3, 12),
        'description': 'Proposed two-storey medical and dental diagnostic clinic with dedicated commercial parking.',
        'lat': 11.3008,
        'lng': 124.6925,
        'fulfill_ratio': 0.8,
    },
    {
        'title': '#OP-2026-0089 — Engr. Rodolfo T. Tan',
        'permit_number': 'OP-2026-0089',
        'applicant_name': 'Engr. Rodolfo T. Tan',
        'permit_type': 'Occupancy',
        'building_type': 'Residential',
        'barangay_name': 'Sawang (Poblacion)',
        'year': 2026,
        'date_issued': date(2026, 4, 5),
        'description': 'Certificate of Occupancy for completed two-storey reinforced concrete residential dwelling.',
        'lat': 11.2995,
        'lng': 124.6890,
        'fulfill_ratio': 1.0,
    },
    {
        'title': '#EP-2025-0311 — Ma. Teresa G. Cruz',
        'permit_number': 'EP-2025-0311',
        'applicant_name': 'Ma. Teresa G. Cruz',
        'permit_type': 'Electrical',
        'building_type': 'Commercial',
        'barangay_name': 'Baybay (Poblacion)',
        'year': 2025,
        'date_issued': date(2025, 11, 18),
        'description': 'Three-phase electrical power service connection and 50kVA step-down transformer installation.',
        'lat': 11.3015,
        'lng': 124.6882,
        'fulfill_ratio': 0.6,
    },
    {
        'title': '#FP-2025-0104 — Antonio V. Veloso',
        'permit_number': 'FP-2025-0104',
        'applicant_name': 'Antonio V. Veloso',
        'permit_type': 'Fencing',
        'building_type': 'Residential',
        'barangay_name': 'Barugohay Norte',
        'year': 2025,
        'date_issued': date(2025, 8, 22),
        'description': 'Perimeter boundary fence with decorative hollow blocks and reinforced concrete posts.',
        'lat': 11.3120,
        'lng': 124.6810,
        'fulfill_ratio': 0.5,
    },
    {
        'title': '#BP-2024-0275 — Carigara Agro-Industrial Corp.',
        'permit_number': 'BP-2024-0275',
        'applicant_name': 'Carigara Agro-Industrial Corp. (c/o L. Gomez)',
        'permit_type': 'Building',
        'building_type': 'Industrial',
        'barangay_name': 'Guindapunan East',
        'year': 2024,
        'date_issued': date(2024, 6, 14),
        'description': 'Steel-framed grain drying and storage warehouse facility with covered loading bay.',
        'lat': 11.3040,
        'lng': 124.7010,
        'fulfill_ratio': 1.0,
    },
]

SAMPLE_PROJECTS = [
    {
        'title': 'Concreting of Barangay Farm-to-Market Road Phase 2',
        'project_scope': 'Municipal',
        'project_type': 'Roads and Bridges',
        'funding_source': '20% Development Fund',
        'funding_source_other': '',
        'contractor': 'Eastern Leyte Builders & Supply Corp.',
        'project_cost': 4850000.00,
        'barangay_name': 'Balilit',
        'year': 2026,
        'date_started': date(2026, 1, 15),
        'date_completed': date(2026, 4, 20),
        'description': '1.2km standard concrete road pavement, aggregate base course, and slope protection stone masonry.',
        'lat': 11.2850,
        'lng': 124.6750,
        'fulfill_ratio': 0.7,
    },
    {
        'title': 'Construction of 2-Storey Multi-Purpose Evacuation Center',
        'project_scope': 'Municipal',
        'project_type': 'Vertical Structures',
        'funding_source': 'LDRRM Fund',
        'funding_source_other': '',
        'contractor': 'Carigara Premier Construction Corp.',
        'project_cost': 8750000.00,
        'barangay_name': 'Canfabi',
        'year': 2025,
        'date_started': date(2025, 4, 10),
        'date_completed': date(2025, 12, 18),
        'description': 'Disaster-resilient evacuation hall complete with elevated comfort rooms, kitchen, and power supply.',
        'lat': 11.2980,
        'lng': 124.6650,
        'fulfill_ratio': 1.0,
    },
    {
        'title': 'Rehabilitation of Carigara River Flood Control Dike',
        'project_scope': 'Municipal',
        'project_type': 'Flood Control and Drainage System',
        'funding_source': 'DPWH',
        'funding_source_other': '',
        'contractor': 'Leyte Hydroworks Joint Venture',
        'project_cost': 12300000.00,
        'barangay_name': 'Barugohay Central',
        'year': 2025,
        'date_started': date(2025, 2, 1),
        'date_completed': date(2025, 9, 30),
        'description': 'Revetment wall construction with steel sheet piles and gabion mattress riverbank protection.',
        'lat': 11.3050,
        'lng': 124.6850,
        'fulfill_ratio': 0.8,
    },
    {
        'title': 'Installation of Solar-Powered Level II Potable Water System',
        'project_scope': 'Barangay',
        'project_type': 'Potable Water System',
        'funding_source': 'Barangay Fund',
        'funding_source_other': '',
        'contractor': 'By Administration (LGU Carigara)',
        'project_cost': 1450000.00,
        'barangay_name': 'Binibihan',
        'year': 2026,
        'date_started': date(2026, 2, 5),
        'date_completed': date(2026, 4, 15),
        'description': 'Submersible deep well pump, stainless storage reservoir tank, and communal public tap stands.',
        'lat': 11.2720,
        'lng': 124.6980,
        'fulfill_ratio': 0.6,
    },
    {
        'title': 'Construction of Covered Barangay Sports and Cultural Center',
        'project_scope': 'Barangay',
        'project_type': 'Vertical Structures',
        'funding_source': 'LGU General Fund',
        'funding_source_other': '',
        'contractor': 'Vanguard Engineering & Builders',
        'project_cost': 3200000.00,
        'barangay_name': 'Bislig',
        'year': 2024,
        'date_started': date(2024, 7, 1),
        'date_completed': date(2024, 11, 28),
        'description': 'Structural steel truss covered court with acrylic sports flooring and stage facility.',
        'lat': 11.2890,
        'lng': 124.7080,
        'fulfill_ratio': 1.0,
    },
]

SAMPLE_ILLEGAL_CONSTRUCTIONS = [
    {
        'title': 'Unauthorized 2-Storey Commercial Retail Building',
        'applicant_name': 'Vicente M. Alcantara',
        'barangay_name': 'Baybay (Poblacion)',
        'year': 2026,
        'compliance_status': 'unresolved',
        'description': 'Active ongoing construction of 2-storey commercial building without approved building permit. 1st Notice of Violation served.',
        'lat': 11.3022,
        'lng': 124.6892,
    },
    {
        'title': 'Encroachment on Barangay Road Right-of-Way (Steel Awning)',
        'applicant_name': 'Corazon D. Ramos',
        'barangay_name': 'Barugohay Sur',
        'year': 2026,
        'compliance_status': 'unresolved',
        'description': 'Permanent steel framing and roof canopy encroaching 1.8 meters into public road right-of-way corridor.',
        'lat': 11.3080,
        'lng': 124.6790,
    },
    {
        'title': 'Unlicensed Fuel Dispensing Shed and Storage Facility',
        'applicant_name': 'Danilo F. Torrevillas',
        'barangay_name': 'Canal',
        'year': 2025,
        'compliance_status': 'unresolved',
        'description': 'Hazardous fuel dispensing shed constructed without fire safety clearance and municipal building permit.',
        'lat': 11.2950,
        'lng': 124.6910,
    },
    {
        'title': 'Commercial Extension & Auto Repair Bay (Complied)',
        'applicant_name': 'Felipe B. Salazar',
        'barangay_name': 'Jugaban (Poblacion)',
        'year': 2025,
        'compliance_status': 'resolved',
        'description': 'Originally flagged for unauthorized extension. Owner submitted structural plans and secured approved Building Permit #BP-2025-0199.',
        'lat': 11.3012,
        'lng': 124.6940,
    },
    {
        'title': 'Concrete Perimeter Firewall Overheight Violation (Resolved)',
        'applicant_name': 'Lourdes P. Hermosa',
        'barangay_name': 'Balilit',
        'year': 2024,
        'compliance_status': 'resolved',
        'description': 'Disputed 4-meter firewall adjoining adjacent boundary. Resolved after site reinspection and approved revised setback clearance.',
        'lat': 11.2865,
        'lng': 124.6740,
    },
]

SAMPLE_TRASH_RECORDS = [
    {
        'record_type': 'Permit',
        'title': '#BP-2026-0044 — Arnaldo C. Gutierrez',
        'applicant_name': 'Arnaldo C. Gutierrez',
        'permit_type': 'Building',
        'building_type': 'Residential',
        'barangay_name': 'Candigahub',
        'year': 2026,
        'days_in_trash': 2,  # 28 days left
        'description': 'Cancelled building permit application due to property boundary dispute.',
    },
    {
        'record_type': 'Permit',
        'title': '#FP-2026-0019 — Salvacion K. Navarro',
        'applicant_name': 'Salvacion K. Navarro',
        'permit_type': 'Fencing',
        'building_type': 'Residential',
        'barangay_name': 'Caghalo',
        'year': 2026,
        'days_in_trash': 8,  # 22 days left
        'description': 'Duplicate fencing permit entry deleted by applicant request.',
    },
    {
        'record_type': 'Project',
        'title': 'Emergency Riprap Slope Protection (Replaced by Phase 2)',
        'project_scope': 'Municipal',
        'project_type': 'Flood Control and Drainage System',
        'funding_source': 'LDRRM Fund',
        'contractor': 'By Administration (LGU Carigara)',
        'barangay_name': 'Camansi',
        'year': 2025,
        'days_in_trash': 15,  # 15 days left
        'description': 'Obsolete draft project scope merged into comprehensive municipal flood control master plan.',
    },
    {
        'record_type': 'Permit',
        'is_illegal': True,
        'title': 'Unauthorized Roadside Kiosk Structure (Voluntarily Dismantled)',
        'applicant_name': 'Gregorio M. Perez',
        'barangay_name': 'Barayong',
        'year': 2025,
        'days_in_trash': 23,  # 7 days left (expiring soon warning)
        'description': 'Temporary timber structure cleared and voluntarily removed by owner following notice.',
    },
    {
        'record_type': 'Project',
        'title': 'Proposed Solar Streetlighting Installation Pilot',
        'project_scope': 'Barangay',
        'project_type': 'Roads and Bridges',
        'funding_source': 'Barangay Fund',
        'contractor': 'Eastern Leyte Builders & Supply Corp.',
        'barangay_name': 'Canlampay',
        'year': 2024,
        'days_in_trash': 27,  # 3 days left (expiring soon warning)
        'description': 'Archived project record scheduled for 30-day automated purge.',
    },
]


def seed_all_demo_data(stdout=None, style=None):
    """Core seeding logic callable from management command or admin view."""
    def log(msg, is_success=False):
        if stdout:
            if is_success and style:
                stdout.write(style.SUCCESS(msg))
            else:
                stdout.write(msg)
        else:
            print(msg)

    # 1. Master user
    admin_user = CustomUser.objects.filter(role__in=['admin', 'staff']).first()
    if not admin_user:
        admin_pass = os.environ.get('SEED_ADMIN_PASSWORD', 'eTala@2026')
        admin_user = CustomUser.objects.create_user(
            username=os.environ.get('SEED_ADMIN_USERNAME', 'admin'),
            email=os.environ.get('SEED_ADMIN_EMAIL', 'carigaraetala@gmail.com'),
            password=admin_pass,
            role='admin',
            is_staff=True,
            is_superuser=True,
            full_name='System Administrator',
            designation='Municipal Engineer'
        )
        log(f"Created fallback Admin: {admin_user.username}")

    default_brgy = Barangay.objects.first()
    results = {
        'permits_created': 0,
        'projects_created': 0,
        'violations_created': 0,
        'trash_created': 0,
    }

    # ── 1. Seed Realistic Permits ──
    log("Seeding Realistic Permits...")
    for p in SAMPLE_PERMITS:
        if EngineeringRecord.objects.filter(title=p['title']).exists():
            log(f"  [SKIP] Permit '{p['title']}' already exists.")
            continue

        brgy = Barangay.objects.filter(barangay_name__iexact=p['barangay_name']).first() or default_brgy
        rec = EngineeringRecord.objects.create(
            record_type='Permit',
            project_scope='',
            barangay=brgy,
            title=p['title'],
            year=p['year'],
            description=p['description'],
            status='active',
            is_illegal_construction=False,
            latitude=p['lat'],
            longitude=p['lng'],
            date_started=p['date_issued'],
            created_by=admin_user,
        )

        PermitDetail.objects.create(
            engineering_record=rec,
            permit_type=p['permit_type'],
            building_type=p['building_type'],
            permit_number=p['permit_number'],
            applicant_name=p['applicant_name'],
            date_issued=p['date_issued'],
            remarks=p['description']
        )

        # Requirements
        tmpl = RequirementTemplate.objects.filter(record_type='Permit', subtype=p['permit_type']).first()
        if tmpl:
            items = list(tmpl.active_items)
            cutoff = int(len(items) * p['fulfill_ratio'])
            for idx, item in enumerate(items):
                rr = RecordRequirement.objects.create(record=rec, requirement_item=item)
                if idx < cutoff and not item.is_parent_group:
                    safe_fn = f"{item.name.replace(' ', '_').lower()}_{rec.record_id}.pdf"
                    doc = Document.objects.create(
                        engineering_record=rec,
                        requirement_item=item,
                        document_type=item.name[:50],
                        file=ContentFile(DUMMY_PDF_BYTES, name=safe_fn),
                        file_name=safe_fn,
                        file_size=len(DUMMY_PDF_BYTES),
                        version=1,
                        uploaded_by=admin_user
                    )
                    rr.document = doc
                    rr.is_fulfilled = True
                    rr.fulfilled_at = timezone.now()
                    rr.fulfilled_by = admin_user
                    rr.save()

        AuditLog.objects.create(
            user=admin_user,
            action=f"Created {p['permit_type']} Permit record #{p['permit_number']}",
            target_record_id=rec.record_id,
            ip_address='127.0.0.1'
        )
        results['permits_created'] += 1
        log(f"  [+] Created Permit: {p['title']}")

    # ── 2. Seed Realistic Projects ──
    log("Seeding Realistic Infrastructure Projects...")
    for prj in SAMPLE_PROJECTS:
        if EngineeringRecord.objects.filter(title=prj['title']).exists():
            log(f"  [SKIP] Project '{prj['title']}' already exists.")
            continue

        brgy = Barangay.objects.filter(barangay_name__iexact=prj['barangay_name']).first() or default_brgy
        rec = EngineeringRecord.objects.create(
            record_type='Project',
            project_scope=prj['project_scope'],
            barangay=brgy,
            title=prj['title'],
            year=prj['year'],
            description=prj['description'],
            status='active',
            is_illegal_construction=False,
            latitude=prj['lat'],
            longitude=prj['lng'],
            date_started=prj['date_started'],
            date_completed=prj['date_completed'],
            created_by=admin_user,
        )

        ProjectDetail.objects.create(
            engineering_record=rec,
            project_type=prj['project_type'],
            funding_source=prj['funding_source'],
            funding_source_other=prj['funding_source_other'],
            contractor=prj['contractor'],
            project_cost=prj['project_cost'],
            project_status='Completed'
        )

        # Requirements
        tmpl = RequirementTemplate.objects.filter(record_type='Project', subtype=prj['project_type']).first()
        if tmpl:
            items = list(tmpl.active_items)
            cutoff = int(len(items) * prj['fulfill_ratio'])
            for idx, item in enumerate(items):
                rr = RecordRequirement.objects.create(record=rec, requirement_item=item)
                if idx < cutoff and not item.is_parent_group:
                    safe_fn = f"{item.name.replace(' ', '_').lower()}_{rec.record_id}.pdf"
                    doc = Document.objects.create(
                        engineering_record=rec,
                        requirement_item=item,
                        document_type=item.name[:50],
                        file=ContentFile(DUMMY_PDF_BYTES, name=safe_fn),
                        file_name=safe_fn,
                        file_size=len(DUMMY_PDF_BYTES),
                        version=1,
                        uploaded_by=admin_user
                    )
                    rr.document = doc
                    rr.is_fulfilled = True
                    rr.fulfilled_at = timezone.now()
                    rr.fulfilled_by = admin_user
                    rr.save()

        AuditLog.objects.create(
            user=admin_user,
            action=f"Created Project record: {prj['title']}",
            target_record_id=rec.record_id,
            ip_address='127.0.0.1'
        )
        results['projects_created'] += 1
        log(f"  [+] Created Project: {prj['title']}")

    # ── 3. Seed Illegal Constructions ──
    log("Seeding Illegal Constructions (Violations)...")
    for ill in SAMPLE_ILLEGAL_CONSTRUCTIONS:
        if EngineeringRecord.objects.filter(title=ill['title']).exists():
            log(f"  [SKIP] Illegal Construction '{ill['title']}' already exists.")
            continue

        brgy = Barangay.objects.filter(barangay_name__iexact=ill['barangay_name']).first() or default_brgy
        rec = EngineeringRecord.objects.create(
            record_type='Permit',
            project_scope='',
            barangay=brgy,
            title=ill['title'],
            year=ill['year'],
            description=ill['description'],
            status='active',
            is_illegal_construction=True,
            illegal_compliance_status=ill['compliance_status'],
            latitude=ill['lat'],
            longitude=ill['lng'],
            date_started=date(ill['year'], 3, 1),
            created_by=admin_user,
        )

        PermitDetail.objects.create(
            engineering_record=rec,
            permit_type='Building',
            building_type='Commercial',
            applicant_name=ill['applicant_name'],
            remarks=ill['description']
        )

        # Upload discovery picture evidence
        safe_fn = f"violation_evidence_{rec.record_id}.pdf"
        Document.objects.create(
            engineering_record=rec,
            document_type='Picture',
            file=ContentFile(DUMMY_PDF_BYTES, name=safe_fn),
            file_name=safe_fn,
            file_size=len(DUMMY_PDF_BYTES),
            version=1,
            uploaded_by=admin_user
        )

        AuditLog.objects.create(
            user=admin_user,
            action=f"Reported Illegal Construction: {ill['title']}",
            target_record_id=rec.record_id,
            ip_address='127.0.0.1'
        )
        results['violations_created'] += 1
        log(f"  [+] Created Violation ({ill['compliance_status']}): {ill['title']}")

    # ── 4. Seed Trash / Soft-deleted Records ──
    log("Seeding Trash / Archived Records (Demonstrating 30-Day Retention Countdown)...")
    now = timezone.now()
    for tr in SAMPLE_TRASH_RECORDS:
        if EngineeringRecord.objects.filter(title=tr['title']).exists():
            log(f"  [SKIP] Trash record '{tr['title']}' already exists.")
            continue

        brgy = Barangay.objects.filter(barangay_name__iexact=tr['barangay_name']).first() or default_brgy
        deleted_timestamp = now - timedelta(days=tr['days_in_trash'])
        is_ill = tr.get('is_illegal', False)

        rec = EngineeringRecord.objects.create(
            record_type=tr['record_type'],
            project_scope=tr.get('project_scope', ''),
            barangay=brgy,
            title=tr['title'],
            year=tr['year'],
            description=tr['description'],
            status='archived',
            is_illegal_construction=is_ill,
            illegal_compliance_status='unresolved' if is_ill else '',
            created_by=admin_user,
            deleted_at=deleted_timestamp,
        )

        if tr['record_type'] == 'Permit':
            PermitDetail.objects.create(
                engineering_record=rec,
                permit_type=tr.get('permit_type', 'Building'),
                building_type=tr.get('building_type', 'Residential'),
                applicant_name=tr.get('applicant_name', ''),
                remarks=tr['description']
            )
        else:
            ProjectDetail.objects.create(
                engineering_record=rec,
                project_type=tr.get('project_type', 'Roads and Bridges'),
                funding_source=tr.get('funding_source', 'LGU General Fund'),
                contractor=tr.get('contractor', ''),
                project_cost=2500000.00,
                project_status='Completed'
            )

        AuditLog.objects.create(
            user=admin_user,
            action=f"Moved to Trash: {tr['title']}",
            target_record_id=rec.record_id,
            ip_address='127.0.0.1'
        )
        results['trash_created'] += 1
        log(f"  [+] Created Trash Record ({30 - tr['days_in_trash']}d left): {tr['title']}")

    log(f"Finished Demo Seeding: {results}", is_success=True)
    return results


class Command(BaseCommand):
    help = 'Seeds realistic, deletable demo records (Permits, Projects, Violations, Trash retention)'

    def handle(self, *args, **options):
        seed_all_demo_data(stdout=self.stdout, style=self.style)
