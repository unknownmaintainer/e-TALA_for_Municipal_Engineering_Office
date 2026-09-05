"""
Management command: seed_electrical_permits

Seeds sample Electrical Permit records with YYYY-MM-XXXX formatted numbers,
associated barangays in Carigara, Leyte, and document attachments for testing and demonstration.
"""
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone
from datetime import date
from permits.models import CustomUser, Barangay, EngineeringRecord, PermitDetail, RequirementTemplate, RecordRequirement, Document


SAMPLE_ELECTRICAL_PERMITS = [
    {
        'permit_number': '2026-02-0001',
        'applicant_name': 'Rolando Tan & Family',
        'building_type': 'Residential',
        'barangay_name': 'Jugaban (Poblacion)',
        'date_issued': date(2026, 2, 10),
        'remarks': 'New single-phase 230V residential electrical service installation.',
        'lat': 11.3007,
        'lng': 124.6934,
    },
    {
        'permit_number': '2026-03-0004',
        'applicant_name': 'Carigara Commercial Hub (c/o Elena Ramos)',
        'building_type': 'Commercial',
        'barangay_name': 'Baybay (Poblacion)',
        'date_issued': date(2026, 3, 15),
        'remarks': 'Three-phase 460V commercial transformer and main distribution panel upgrade.',
        'lat': 11.3011,
        'lng': 124.6889,
    },
    {
        'permit_number': '2025-11-0012',
        'applicant_name': 'Engr. Francisco Mendoza',
        'building_type': 'Industrial',
        'barangay_name': 'Guindapunan East',
        'date_issued': date(2025, 11, 20),
        'remarks': 'Industrial rice milling plant motor control center and backup generator wiring.',
        'lat': 11.3037,
        'lng': 124.7004,
    },
    {
        'permit_number': '2025-08-0008',
        'applicant_name': 'Maria Lourdes Gonzaga',
        'building_type': 'Residential',
        'barangay_name': 'Ponong (Poblacion)',
        'date_issued': date(2025, 8, 5),
        'remarks': 'Residential rewire and solar PV interconnection system.',
        'lat': 11.2977,
        'lng': 124.6829,
    },
    {
        'permit_number': '2024-05-0019',
        'applicant_name': 'St. Joseph Cold Storage Facility',
        'building_type': 'Commercial',
        'barangay_name': 'Sawang (Poblacion)',
        'date_issued': date(2024, 5, 12),
        'remarks': 'Refrigeration circuit installation and emergency backup transfer switch.',
        'lat': 11.2993,
        'lng': 124.6895,
    }
]

# Minimal valid PDF binary content for testing
DUMMY_PDF_BYTES = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n"


class Command(BaseCommand):
    help = 'Seeds sample Electrical Permits with official YYYY-MM-XXXX numbers and mock PDF documents.'

    def handle(self, *args, **options):
        self.stdout.write("Seeding Electrical Permits...")

        # Get or create an admin/staff user
        user = CustomUser.objects.filter(role__in=['admin', 'staff']).first()
        if not user:
            admin_pass = os.environ.get('SEED_ADMIN_PASSWORD', 'admin123')
            user = CustomUser.objects.create_user(
                username=os.environ.get('SEED_ADMIN_USERNAME', 'admin'),
                email=os.environ.get('SEED_ADMIN_EMAIL', 'admin@gmail.com'),
                password=admin_pass,
                role='admin',
                full_name='Municipal Engineering Admin'
            )

        # Get electrical template
        elec_template = RequirementTemplate.objects.filter(record_type='Permit', subtype='Electrical').first()

        created_count = 0
        for item in SAMPLE_ELECTRICAL_PERMITS:
            b_name = item['barangay_name']
            brgy = Barangay.objects.filter(barangay_name__iexact=b_name).first()
            if not brgy:
                brgy = Barangay.objects.first()

            p_num = item['permit_number']
            title = f"{p_num} — {item['applicant_name']}"

            # Check if already exists
            existing = PermitDetail.objects.filter(permit_number__iexact=p_num).first()
            if existing:
                self.stdout.write(f"  [SKIP] Electrical Permit #{p_num} already exists.")
                continue

            rec = EngineeringRecord.objects.create(
                record_type='Permit',
                project_scope='',
                barangay=brgy,
                title=title,
                year=item['date_issued'].year,
                description=item['remarks'],
                status='active',
                is_illegal_construction=False,
                latitude=item['lat'],
                longitude=item['lng'],
                created_by=user,
            )

            p_detail = PermitDetail.objects.create(
                engineering_record=rec,
                permit_type='Electrical',
                building_type=item['building_type'],
                permit_number=p_num,
                applicant_name=item['applicant_name'],
                date_issued=item['date_issued'],
                remarks=item['remarks']
            )

            # Assign requirements checklist if template exists
            if elec_template:
                for req_item in elec_template.active_items:
                    record_req = RecordRequirement.objects.create(
                        record=rec,
                        requirement_item=req_item
                    )
                    # For top requirements, attach a mock PDF document
                    if not req_item.is_parent_group and ('Permit' in req_item.name or 'Clearance' in req_item.name or 'Picture' in req_item.name):
                        safe_filename = f"{req_item.name.replace(' ', '_').lower()}_{p_num}.pdf"
                        doc_file = ContentFile(DUMMY_PDF_BYTES, name=safe_filename)
                        doc = Document.objects.create(
                            engineering_record=rec,
                            requirement_item=req_item,
                            document_type=req_item.name[:50],
                            file=doc_file,
                            file_name=safe_filename,
                            file_size=len(DUMMY_PDF_BYTES),
                            version=1,
                            uploaded_by=user
                        )
                        record_req.document = doc
                        record_req.is_fulfilled = True
                        record_req.fulfilled_at = timezone.now()
                        record_req.fulfilled_by = user
                        record_req.save()

            created_count += 1
            self.stdout.write(f"  [+] Created Electrical Permit: {p_num} - {item['applicant_name']}")

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {created_count} Electrical Permits."))
