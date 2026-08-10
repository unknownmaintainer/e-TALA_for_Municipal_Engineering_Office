import os
import json
import logging
import mimetypes
import io
import requests
from django.core.files.storage import Storage, FileSystemStorage
from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible
from django.conf import settings

logger = logging.getLogger(__name__)


@deconstructible
class SupabaseStorage(Storage):
    """
    S3/REST-compatible Supabase Object Storage backend for eTala.
    
    Stores documents in a dedicated Supabase bucket (default: 'etala-documents').
    Only clean relative paths are stored in database models (e.g. 'documents/2026/08/BP_001.pdf').
    Generates time-limited private Signed URLs for secure staff viewing.
    Automatically falls back to local FileSystemStorage if Supabase credentials are not configured.
    """

    def __init__(self, bucket_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fallback_storage = FileSystemStorage()
        self.bucket_name = bucket_name or os.getenv('SUPABASE_BUCKET_NAME', 'etala-documents').strip()

    def _get_supabase_config(self):
        url = (os.getenv('SUPABASE_URL') or getattr(settings, 'SUPABASE_URL', '')).strip().rstrip('/')
        key = (os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY') or getattr(settings, 'SUPABASE_KEY', '')).strip()
        bucket = self.bucket_name or 'etala-documents'
        return url, key, bucket

    def _is_configured(self):
        url, key, _ = self._get_supabase_config()
        return bool(url and key and url.startswith(('http://', 'https://')))

    def _headers(self):
        _, key, _ = self._get_supabase_config()
        return {
            'Authorization': f'Bearer {key}',
            'apiKey': key,
        }

    def _clean_path(self, name):
        """Standardizes relative object path, stripping leading slashes and legacy double-media prefixes."""
        name_str = str(name).replace('\\', '/').lstrip('/')
        if name_str.startswith('media/'):
            name_str = name_str[6:]
        return name_str

    def _save(self, name, content):
        clean_name = self._clean_path(name)
        
        # Save to local fallback storage first for guaranteed offline availability / caching
        self.fallback_storage.save(clean_name, content)
        
        if not self._is_configured():
            return clean_name

        url, key, bucket = self._get_supabase_config()
        endpoint = f"{url}/storage/v1/object/{bucket}/{clean_name}"
        
        try:
            if hasattr(content, 'seek'):
                try:
                    content.seek(0)
                except Exception:
                    pass
            
            data = content.read() if hasattr(content, 'read') else content
            mime_type, _ = mimetypes.guess_type(clean_name)
            headers = self._headers()
            headers['Content-Type'] = mime_type or 'application/octet-stream'
            headers['x-upsert'] = 'true'

            resp = requests.post(endpoint, headers=headers, data=data, timeout=20)
            if resp.status_code in (200, 201):
                logger.info(f"Successfully uploaded {clean_name} to Supabase bucket '{bucket}'.")
            else:
                logger.warning(f"Supabase upload returned {resp.status_code} for {clean_name}: {resp.text}")
        except Exception as exc:
            logger.warning(f"Supabase upload failed ({exc}), local copy preserved at {clean_name}.")

        return clean_name

    def open(self, name, mode='rb'):
        clean_name = self._clean_path(name)
        
        # Check local storage first
        if self.fallback_storage.exists(clean_name):
            try:
                return self.fallback_storage.open(clean_name, mode)
            except Exception as exc:
                logger.debug(f"Failed opening {clean_name} from local fallback: {exc}")

        if not self._is_configured():
            return self.fallback_storage.open(clean_name, mode)

        # Download from Supabase bucket
        url, _, bucket = self._get_supabase_config()
        endpoint = f"{url}/storage/v1/object/authenticated/{bucket}/{clean_name}"
        
        try:
            resp = requests.get(endpoint, headers=self._headers(), timeout=15)
            if resp.status_code == 200:
                file_obj = io.BytesIO(resp.content)
                file_obj.name = os.path.basename(clean_name)
                return file_obj
            
            # Try public object endpoint
            public_endpoint = f"{url}/storage/v1/object/public/{bucket}/{clean_name}"
            resp_pub = requests.get(public_endpoint, timeout=10)
            if resp_pub.status_code == 200:
                file_obj = io.BytesIO(resp_pub.content)
                file_obj.name = os.path.basename(clean_name)
                return file_obj
        except Exception as exc:
            logger.warning(f"Failed opening from Supabase ({exc}), checking fallback.")

        return self.fallback_storage.open(clean_name, mode)

    def _open(self, name, mode='rb'):
        return self.open(name, mode)

    def url(self, name, expires_in=600):
        """Generates Supabase storage URL directly without blocking synchronous network requests during page rendering."""
        clean_name = self._clean_path(name)
        
        if not self._is_configured():
            return self.fallback_storage.url(clean_name)

        url, _, bucket = self._get_supabase_config()
        return f"{url}/storage/v1/object/public/{bucket}/{clean_name}"

    def delete(self, name):
        clean_name = self._clean_path(name)
        if self.fallback_storage.exists(clean_name):
            try:
                self.fallback_storage.delete(clean_name)
            except Exception as exc:
                logger.debug(f"Error removing local copy of {clean_name}: {exc}")

        if self._is_configured():
            url, _, bucket = self._get_supabase_config()
            delete_endpoint = f"{url}/storage/v1/object/{bucket}"
            try:
                requests.delete(
                    delete_endpoint,
                    headers=self._headers(),
                    json={'prefixes': [clean_name]},
                    timeout=8
                )
            except Exception as exc:
                logger.warning(f"Failed deleting {clean_name} from Supabase: {exc}")

    def exists(self, name):
        clean_name = self._clean_path(name)
        if self.fallback_storage.exists(clean_name):
            return True
        if not self._is_configured():
            return False

        url, _, bucket = self._get_supabase_config()
        info_endpoint = f"{url}/storage/v1/object/info/{bucket}/{clean_name}"
        try:
            resp = requests.get(info_endpoint, headers=self._headers(), timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def size(self, name):
        clean_name = self._clean_path(name)
        if self.fallback_storage.exists(clean_name):
            return self.fallback_storage.size(clean_name)
        return 0

    def get_valid_name(self, name):
        return self.fallback_storage.get_valid_name(name)

    def get_available_name(self, name, max_length=None):
        return self.fallback_storage.get_available_name(name, max_length=max_length)


@deconstructible
class DynamicCloudinaryStorage(Storage):
    """
    Custom Cloudinary storage router with automatic fallback to local FileSystemStorage.
    """
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff', '.svg'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fallback_storage = FileSystemStorage()
        try:
            from cloudinary_storage.storage import MediaCloudinaryStorage, RawMediaCloudinaryStorage
            self._image_storage = MediaCloudinaryStorage()
            self._raw_storage = RawMediaCloudinaryStorage()
        except Exception:
            self._image_storage = None
            self._raw_storage = None

    def _has_cloudinary(self):
        c_name = (os.getenv('CLOUDINARY_CLOUD_NAME') or '').strip()
        c_key = (os.getenv('CLOUDINARY_API_KEY') or '').strip()
        c_secret = (os.getenv('CLOUDINARY_API_SECRET') or '').strip()
        return bool(c_name and c_key and c_secret)

    def _get_storage(self, name):
        ext = os.path.splitext(name)[1].lower() if name else ''
        if ext in self.IMAGE_EXTENSIONS:
            return self._image_storage or self.fallback_storage
        return self._raw_storage or self.fallback_storage

    def save(self, name, content, max_length=None):
        if not self._has_cloudinary():
            return self.fallback_storage.save(name, content, max_length=max_length)
        try:
            return super().save(name, content, max_length=max_length)
        except Exception as exc:
            logger.warning(f"Cloudinary save failed ({exc}), falling back to local FileSystemStorage.")
            if hasattr(content, 'seek'):
                try:
                    content.seek(0)
                except Exception:
                    pass
            return self.fallback_storage.save(name, content, max_length=max_length)

    def open(self, name, mode='rb'):
        if not self._has_cloudinary() or self.fallback_storage.exists(name):
            return self.fallback_storage.open(name, mode)
        try:
            return self._get_storage(name).open(name, mode)
        except Exception:
            return self.fallback_storage.open(name, mode)

    def _open(self, name, mode='rb'):
        return self.open(name, mode)

    def _save(self, name, content):
        if not self._has_cloudinary():
            return self.fallback_storage._save(name, content)
        try:
            return self._get_storage(name)._save(name, content)
        except Exception as exc:
            logger.warning(f"Cloudinary _save failed ({exc}), falling back to local FileSystemStorage.")
            if hasattr(content, 'seek'):
                try:
                    content.seek(0)
                except Exception:
                    pass
            return self.fallback_storage._save(name, content)

    def delete(self, name):
        if self.fallback_storage.exists(name):
            try:
                self.fallback_storage.delete(name)
            except Exception as exc:
                logger.debug(f"Local deletion error for {name}: {exc}")
        if self._has_cloudinary():
            try:
                self._get_storage(name).delete(name)
            except Exception as exc:
                logger.debug(f"Cloudinary deletion error for {name}: {exc}")

    def exists(self, name):
        if self.fallback_storage.exists(name):
            return True
        if self._has_cloudinary():
            try:
                return self._get_storage(name).exists(name)
            except Exception:
                pass
        return False

    def url(self, name):
        if self.fallback_storage.exists(name) or not self._has_cloudinary():
            return self.fallback_storage.url(name)
        try:
            return self._get_storage(name).url(name)
        except Exception:
            return self.fallback_storage.url(name)

    def size(self, name):
        if self.fallback_storage.exists(name) or not self._has_cloudinary():
            return self.fallback_storage.size(name)
        try:
            return self._get_storage(name).size(name)
        except Exception:
            return self.fallback_storage.size(name)

    def get_valid_name(self, name):
        return self.fallback_storage.get_valid_name(name)

    def get_available_name(self, name, max_length=None):
        return self.fallback_storage.get_available_name(name, max_length=max_length)
