import os
import json
import logging
import mimetypes
import io
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.core.files.storage import Storage, FileSystemStorage
from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible
from django.conf import settings

logger = logging.getLogger(__name__)

# Global persistent connection session for high-throughput Supabase transfers
_http_session = None

def get_http_session():
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        retries = Retry(total=2, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=30, max_retries=retries)
        _http_session.mount('https://', adapter)
        _http_session.mount('http://', adapter)
    return _http_session


@deconstructible
class SupabaseStorage(Storage):
    """
    High-performance S3/REST-compatible Supabase Object Storage backend for eTala.
    
    Stores documents in a dedicated Supabase bucket (default: 'etala-documents').
    Only clean relative paths are stored in database models (e.g. 'documents/2026/08/BP_001.pdf').
    Automatically caches files locally for ultra-fast response times and seamless offline fallback.
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

    def _find_local_candidate(self, clean_name):
        """Checks multiple candidate local file paths for immediate zero-latency access."""
        base_name = os.path.basename(clean_name)
        candidates = [
            clean_name,
            os.path.join('documents', base_name),
            os.path.join('profile_pictures', base_name),
            base_name,
        ]
        for c in candidates:
            if self.fallback_storage.exists(c):
                return c
        return None

    def _save(self, name, content):
        clean_name = self._clean_path(name)
        
        # Save to local fallback storage first for guaranteed instant availability & caching
        saved_name = self.fallback_storage.save(clean_name, content)
        
        if not self._is_configured():
            return saved_name

        url, key, bucket = self._get_supabase_config()
        endpoint = f"{url}/storage/v1/object/{bucket}/{clean_name}"
        
        try:
            data = b''
            if hasattr(content, 'seek'):
                try:
                    content.seek(0)
                    data = content.read()
                except Exception:
                    pass
            elif hasattr(content, 'read'):
                data = content.read()

            if not data and self.fallback_storage.exists(saved_name):
                with self.fallback_storage.open(saved_name, 'rb') as f:
                    data = f.read()

            mime_type, _ = mimetypes.guess_type(clean_name)
            headers = self._headers()
            headers['Content-Type'] = mime_type or 'application/octet-stream'
            headers['x-upsert'] = 'true'

            session = get_http_session()
            resp = session.post(endpoint, headers=headers, data=data, timeout=(4.0, 15.0))
            if resp.status_code in (200, 201):
                logger.info(f"Successfully uploaded {clean_name} to Supabase bucket '{bucket}'.")
            else:
                logger.warning(f"Supabase upload returned {resp.status_code} for {clean_name}: {resp.text}")
        except Exception as exc:
            logger.warning(f"Supabase upload failed ({exc}), local copy preserved at {clean_name}.")

        return saved_name

    def open(self, name, mode='rb'):
        clean_name = self._clean_path(name)
        
        # 1. Check local storage first (instant 0ms retrieval)
        local_cand = self._find_local_candidate(clean_name)
        if local_cand:
            try:
                return self.fallback_storage.open(local_cand, mode)
            except Exception as exc:
                logger.debug(f"Failed opening local candidate {local_cand}: {exc}")

        if not self._is_configured():
            return self.fallback_storage.open(clean_name, mode)

        # 2. Fast authenticated download from Supabase bucket
        url, _, bucket = self._get_supabase_config()
        endpoint = f"{url}/storage/v1/object/authenticated/{bucket}/{clean_name}"
        
        try:
            session = get_http_session()
            resp = session.get(endpoint, headers=self._headers(), timeout=(3.0, 8.0))
            if resp.status_code == 200:
                content = resp.content
                # Cache locally so subsequent accesses never need a network request
                try:
                    self.fallback_storage.save(clean_name, ContentFile(content))
                except Exception:
                    pass
                file_obj = io.BytesIO(content)
                file_obj.name = os.path.basename(clean_name)
                return file_obj
            elif resp.status_code == 404:
                logger.debug(f"File {clean_name} not found in Supabase bucket '{bucket}'.")
        except Exception as exc:
            logger.warning(f"Supabase download for {clean_name} encountered {exc}. Using fallback.")

        return self.fallback_storage.open(clean_name, mode)

    def _open(self, name, mode='rb'):
        return self.open(name, mode)

    def url(self, name, expires_in=3600):
        """Generates a secure authenticated URL or local fallback URL."""
        clean_name = self._clean_path(name)
        
        if not self._is_configured():
            return self.fallback_storage.url(clean_name)

        url, _, bucket = self._get_supabase_config()
        return f"{url}/storage/v1/object/authenticated/{bucket}/{clean_name}"

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
                session = get_http_session()
                session.delete(
                    delete_endpoint,
                    headers=self._headers(),
                    json={'prefixes': [clean_name]},
                    timeout=(3.0, 6.0)
                )
            except Exception as exc:
                logger.warning(f"Failed deleting {clean_name} from Supabase: {exc}")

    def exists(self, name):
        clean_name = self._clean_path(name)
        if self._find_local_candidate(clean_name):
            return True
        if not self._is_configured():
            return False

        url, _, bucket = self._get_supabase_config()
        endpoint = f"{url}/storage/v1/object/authenticated/{bucket}/{clean_name}"
        try:
            session = get_http_session()
            resp = session.head(endpoint, headers=self._headers(), timeout=(2.0, 4.0))
            if resp.status_code == 200:
                return True
            if resp.status_code == 404:
                return False
        except Exception:
            pass
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
