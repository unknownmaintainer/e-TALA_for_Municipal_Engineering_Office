import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so imports work when running the script directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etala_project.settings')
import django
django.setup()

from permits.models import CustomUser, Document
from django.core.files.storage import default_storage
from django.conf import settings

print('DEFAULT_FILE_STORAGE setting:', getattr(settings, 'DEFAULT_FILE_STORAGE', None))
print('Default storage instance:', f"{default_storage.__class__.__module__}.{default_storage.__class__.__name__}")
from django.utils.module_loading import import_string
try:
    storage_cls = import_string(settings.DEFAULT_FILE_STORAGE)
    print('Imported DEFAULT_FILE_STORAGE class:', f"{storage_cls.__module__}.{storage_cls.__name__}")
    print('DEFAULT_FILE_STORAGE MRO:', storage_cls.__mro__)
    inst = storage_cls()
    print('Instance of DEFAULT_FILE_STORAGE:', f"{inst.__class__.__module__}.{inst.__class__.__name__}")
    print('Instance class MRO:', inst.__class__.__mro__)
    print('Instance has base location:', getattr(inst, 'location', None))
except Exception as e:
    print('Error importing DEFAULT_FILE_STORAGE class:', e)

def print_user_urls(ids):
    for uid in ids:
        try:
            u = CustomUser.objects.get(id=uid)
            storage = getattr(u.profile_picture, 'storage', None)
            storage_desc = f"{storage.__class__.__module__}.{storage.__class__.__name__}" if storage is not None else 'NoStorage'
            print(f"User {uid}: {u.profile_picture.url if u.profile_picture else 'NO FILE'} (storage={storage_desc})")
        except Exception as e:
            print(f"User {uid}: ERROR: {e}")

def print_document_urls(ids):
    for did in ids:
        try:
            d = Document.objects.get(document_id=did)
            storage = getattr(d.file, 'storage', None)
            storage_desc = f"{storage.__class__.__module__}.{storage.__class__.__name__}" if storage is not None else 'NoStorage'
            print(f"Document {did}: {d.file.url if d.file else 'NO FILE'} (storage={storage_desc})")
        except Exception as e:
            print(f"Document {did}: ERROR: {e}")

if __name__ == '__main__':
    user_ids = [1, 2, 3]
    document_ids = [1, 2, 3]
    print_user_urls(user_ids)
    print_document_urls(document_ids)
