import os
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etala_project.settings')
import django
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from permits.views import reports_view
from permits.models import EngineeringRecord, Barangay

User = get_user_model()
admin_user = User.objects.filter(role='admin').first() or User.objects.first()

rf = RequestFactory()

print("==================================================")
print("[LOOP ENGINEERING] Testing Report Views & Exports")
print("==================================================")

scenarios = [
    {"desc": "HTML Report View (Default)", "params": {}},
    {"desc": "HTML Report View (Permits Filter)", "params": {"record_type": "Permit"}},
    {"desc": "HTML Report View (Projects Filter)", "params": {"record_type": "Project"}},
    {"desc": "PDF Export (All Records)", "params": {"export": "pdf"}},
    {"desc": "PDF Export (Permits Only)", "params": {"export": "pdf", "record_type": "Permit"}},
    {"desc": "PDF Export (Projects Only)", "params": {"export": "pdf", "record_type": "Project"}},
    {"desc": "Excel Export (All Records)", "params": {"export": "excel"}},
    {"desc": "Excel Export (Permits Only)", "params": {"export": "excel", "record_type": "Permit"}},
    {"desc": "Excel Export (Projects Only)", "params": {"export": "excel", "record_type": "Project"}},
]

all_passed = True
for s in scenarios:
    req = rf.get('/reports/', s['params'])
    req.user = admin_user
    try:
        response = reports_view(req)
        status = response.status_code
        content_type = response.get('Content-Type', '')
        size = len(response.content) if hasattr(response, 'content') else 0
        if status == 200 and size > 0:
            print(f"  [OK] [{s['desc']}] -> Status 200, Content-Type: {content_type}, Size: {size:,} bytes")
        else:
            print(f"  [FAIL] [{s['desc']}] -> Status {status}, Size: {size}")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] [{s['desc']}] Exception: {e}")
        all_passed = False

print("\n" + "=" * 50)
if all_passed:
    print("ALL REPORT EXPORT TESTS PASSED SUCCESSFULLY!")
else:
    print("SOME TESTS FAILED.")
print("=" * 50)
