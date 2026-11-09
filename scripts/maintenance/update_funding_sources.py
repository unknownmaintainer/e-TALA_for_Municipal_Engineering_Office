import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etala_project.settings')
django.setup()

from permits.models import ProjectDetail, EngineeringRecord

def run_updates():
    print("Migrating funding sources & archiving statuses...")
    
    # 1. Update ProjectDetail funding sources from General Fund to LGU General Fund
    gf_count = ProjectDetail.objects.filter(funding_source__iexact='General Fund').update(funding_source='LGU General Fund')
    print(f"Updated {gf_count} ProjectDetail records to 'LGU General Fund'.")

    # 2. Update default project_status to Completed for pure storage
    ps_count = ProjectDetail.objects.exclude(project_status='Completed').update(project_status='Completed')
    print(f"Updated {ps_count} ProjectDetail records to project_status='Completed'.")

    # 3. Update project EngineeringRecord statuses to completed
    p_rec_count = EngineeringRecord.objects.filter(record_type='Project').exclude(status__in=['completed', 'archived']).update(status='completed')
    print(f"Updated {p_rec_count} Project EngineeringRecords to status='completed'.")

    print("Data migration complete.")

if __name__ == '__main__':
    run_updates()
