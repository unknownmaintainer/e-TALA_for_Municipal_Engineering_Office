import os
import django
import random
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etala_project.settings')
django.setup()

from django.db import transaction
from permits.models import Barangay, CustomUser, EngineeringRecord, PermitDetail, ProjectDetail

def inject_100k():
    print("Preparing 100,000 stress-test records...")
    user = CustomUser.objects.filter(is_superuser=True).first() or CustomUser.objects.first()
    barangays = list(Barangay.objects.all())
    
    if not barangays or not user:
        print("Error: No barangay or user found.")
        return

    permit_types = ['Building', 'Occupancy', 'Fencing', 'Electrical']
    project_types = ['Roads and Bridges', 'Vertical Structures', 'Flood Control and Drainage System', 'Potable Water System']
    project_scopes = ['Municipal', 'Barangay']

    total_to_create = 100000
    batch_size = 5000

    start_time = datetime.now()
    now_dt = datetime.now()

    records_batch = []
    
    print(f"Generating 100,000 record objects in memory...")
    for i in range(total_to_create):
        # 60% Permits, 35% Projects, 5% Violations
        rand_val = random.random()
        b = random.choice(barangays)
        days_ago = random.randint(0, 365)
        rec_dt = now_dt - timedelta(days=days_ago)

        if rand_val < 0.60:
            rec = EngineeringRecord(
                record_type='Permit',
                barangay=b,
                title=f"Regulatory Permit #{i+1}",
                year=rec_dt.year,
                description="Stress test synthetic data record",
                status='active',
                is_illegal_construction=False,
                created_by=user,
            )
            rec.created_at = rec_dt
            rec._permit_type = random.choice(permit_types)
            rec._is_project = False
        elif rand_val < 0.95:
            scope = random.choice(project_scopes)
            rec = EngineeringRecord(
                record_type='Project',
                project_scope=scope,
                barangay=b,
                title=f"Infrastructure Project #{i+1}",
                year=rec_dt.year,
                description="Stress test synthetic data record",
                status='active',
                is_illegal_construction=False,
                created_by=user,
            )
            rec.created_at = rec_dt
            rec._project_cost = round(random.uniform(250000, 15000000), 2)
            rec._project_type = random.choice(project_types)
            rec._is_project = True
        else:
            rec = EngineeringRecord(
                record_type='Permit',
                barangay=b,
                title=f"Notice of Illegal Construction #{i+1}",
                year=rec_dt.year,
                description="Stress test unpermitted construction notice",
                status='pending',
                is_illegal_construction=True,
                illegal_compliance_status=random.choice(['unresolved', 'pending_permit']),
                created_by=user,
            )
            rec.created_at = rec_dt
            rec._permit_type = 'Building'
            rec._is_project = False

        records_batch.append(rec)

    print("Bulk creating 100,000 EngineeringRecord instances...")
    with transaction.atomic():
        created_records = EngineeringRecord.objects.bulk_create(records_batch, batch_size=batch_size)
    
    print(f"Engineering records created. Now creating details in bulk...")
    
    permit_details = []
    project_details = []

    for rec in created_records:
        if getattr(rec, '_is_project', False):
            project_details.append(ProjectDetail(
                engineering_record=rec,
                project_type=getattr(rec, '_project_type', 'Roads and Bridges'),
                project_cost=getattr(rec, '_project_cost', 500000.0),
                contractor="LGU Engineering Task Force",
                funding_source="20% Development Fund"
            ))
        else:
            permit_details.append(PermitDetail(
                engineering_record=rec,
                permit_type=getattr(rec, '_permit_type', 'Building'),
                applicant_name="Carigara Resident / Enterprise",
                permit_number=f"PERM-{rec.record_id}"
            ))

    with transaction.atomic():
        if permit_details:
            PermitDetail.objects.bulk_create(permit_details, batch_size=batch_size)
        if project_details:
            ProjectDetail.objects.bulk_create(project_details, batch_size=batch_size)

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"SUCCESS: Injected 100,000 records in {elapsed:.2f} seconds!")
    print(f"Total Records in DB now: {EngineeringRecord.objects.count():,}")

if __name__ == '__main__':
    inject_100k()
