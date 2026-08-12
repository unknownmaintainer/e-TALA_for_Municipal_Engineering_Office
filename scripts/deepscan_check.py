import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etala_project.settings')
import django
django.setup()

print("--- Testing Django Setup & Module Imports ---")

modules_to_test = [
    'permits.models',
    'permits.validators',
    'permits.storage',
    'permits.middleware',
    'permits.utils',
    'permits.permissions',
    'permits.services',
    'permits.forms',
    'permits.serializers',
    'permits.api_views',
    'permits.views',
    'permits.urls',
]

errors = []
for mod in modules_to_test:
    try:
        __import__(mod)
        print(f"✅ {mod} imported successfully.")
    except Exception as e:
        print(f"❌ ERROR importing {mod}: {e}")
        errors.append((mod, e))

print(f"\nTotal import errors: {len(errors)}")

print("\n--- Testing Model Definitions & Queries ---")
try:
    from permits.models import EngineeringRecord, CustomUser, Barangay, AuditLog, Document
    print(f"EngineeringRecord count: {EngineeringRecord.objects.count()}")
    print(f"CustomUser count: {CustomUser.objects.count()}")
    print(f"Barangay count: {Barangay.objects.count()}")
    print(f"AuditLog count: {AuditLog.objects.count()}")
except Exception as e:
    print(f"❌ ERROR querying models: {e}")
    errors.append(('model_queries', e))

print("\n--- Testing Template Compilation ---")
from django.template.loader import get_template
templates_to_check = [
    'permits/landing.html',
    'permits/login.html',
    'permits/dashboard.html',
    'permits/records_browse.html',
    'permits/record_detail.html',
    'permits/record_create.html',
    'permits/record_edit.html',
    'permits/record_requirement_detail.html',
    'permits/search.html',
    'permits/activity_logs.html',
    'permits/barangays.html',
    'permits/barangay_workspace.html',
    'permits/municipal_projects.html',
    'permits/barangay_projects.html',
    'permits/permit_records.html',
    'permits/archive.html',
    'permits/reports.html',
    'permits/users.html',
    'permits/profile.html',
    'permits/settings.html',
]

template_errors = []
for t in templates_to_check:
    try:
        get_template(t)
        print(f"✅ Template {t} loaded cleanly.")
    except Exception as e:
        print(f"❌ ERROR loading template {t}: {e}")
        template_errors.append((t, e))

print(f"\nTotal template compilation errors: {len(template_errors)}")

if not errors and not template_errors:
    print("\n🎉 ALL MODULES AND TEMPLATES PASSED DEEPSCAN CHECKS WITH ZERO ERRORS!")
