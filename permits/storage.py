import os
import logging
from django.core.files.storage import Storage, FileSystemStorage
from django.utils.deconstruct import deconstructible
from cloudinary_storage.storage import MediaCloudinaryStorage, RawMediaCloudinaryStorage

logger = logging.getLogger(__name__)


@deconstructible
class DynamicCloudinaryStorage(Storage):
    """
    Custom Cloudinary storage router that directs image files (JPG, PNG, WEBP, etc.)
    to MediaCloudinaryStorage (resource_type='image') and document files (DOCX, PDF, etc.)
    to RawMediaCloudinaryStorage (resource_type='raw').

    Includes automatic fallback to local FileSystemStorage if Cloudinary API rejects
    or errors out on specific document file formats.
    """

    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff', '.svg'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image_storage = MediaCloudinaryStorage()
        self.raw_storage = RawMediaCloudinaryStorage()
        self.fallback_storage = FileSystemStorage()

    def _get_storage(self, name):
        ext = os.path.splitext(name)[1].lower() if name else ''
        if ext in self.IMAGE_EXTENSIONS:
            return self.image_storage
        return self.raw_storage

    def _open(self, name, mode='rb'):
        try:
            return self._get_storage(name)._open(name, mode)
        except Exception:
            return self.fallback_storage._open(name, mode)

    def _save(self, name, content):
        storage = self._get_storage(name)
        try:
            return storage._save(name, content)
        except Exception as exc:
            logger.warning(f"Cloudinary save failed for '{name}' ({exc}). Falling back to local FileSystemStorage.")
            if hasattr(content, 'seek'):
                try:
                    content.seek(0)
                except Exception:
                    pass
            return self.fallback_storage._save(name, content)

    def delete(self, name):
        try:
            self._get_storage(name).delete(name)
        except Exception:
            pass
        if self.fallback_storage.exists(name):
            try:
                self.fallback_storage.delete(name)
            except Exception:
                pass

    def exists(self, name):
        try:
            if self._get_storage(name).exists(name):
                return True
        except Exception:
            pass
        return self.fallback_storage.exists(name)

    def url(self, name):
        try:
            if self.fallback_storage.exists(name):
                return self.fallback_storage.url(name)
            return self._get_storage(name).url(name)
        except Exception:
            return self.fallback_storage.url(name)

    def size(self, name):
        try:
            return self._get_storage(name).size(name)
        except Exception:
            return self.fallback_storage.size(name)

    def get_valid_name(self, name):
        return self.fallback_storage.get_valid_name(name)

    def get_available_name(self, name, max_length=None):
        return self.fallback_storage.get_available_name(name, max_length=max_length)
