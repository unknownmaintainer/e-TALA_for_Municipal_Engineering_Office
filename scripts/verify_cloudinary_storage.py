import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'etala_project.settings')
import django
django.setup()

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

print('Storage instance:', type(default_storage))
storage = default_storage

png_bytes = (
    b'\x89PNG\r\n\x1a\n'
    b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
    b'\x00\x00\x00\x0cIDATx\x9cc``\x00\x00\x00\x02\x00\x01E\x0c\x02\x9d'
    b'\x00\x00\x00\x00IEND\xaeB`\x82'
)
name = storage.save('verify_cloudinary_test.png', ContentFile(png_bytes))
print('Saved name:', name)
try:
    print('URL:', storage.url(name))
except Exception as e:
    print('URL error:', e)
storage.delete(name)
print('Deleted test file successfully')
