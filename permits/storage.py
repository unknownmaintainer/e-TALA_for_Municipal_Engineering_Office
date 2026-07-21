import os
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from cloudinary_storage.storage import MediaCloudinaryStorage, RawMediaCloudinaryStorage


@deconstructible
class DynamicCloudinaryStorage(Storage):
    """
    Custom Cloudinary storage router that directs image files (JPG, PNG, WEBP, etc.)
    to MediaCloudinaryStorage (resource_type='image') and document files (DOCX, PDF, etc.)
    to RawMediaCloudinaryStorage (resource_type='raw').

    This prevents Cloudinary API 'Unsupported ZIP file' errors when uploading DOCX/Office
    documents (which are OpenXML ZIP packages).
    """

    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff', '.svg'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image_storage = MediaCloudinaryStorage()
        self.raw_storage = RawMediaCloudinaryStorage()

    def _get_storage(self, name):
        ext = os.path.splitext(name)[1].lower() if name else ''
        if ext in self.IMAGE_EXTENSIONS:
            return self.image_storage
        return self.raw_storage

    def _open(self, name, mode='rb'):
        return self._get_storage(name)._open(name, mode)

    def _save(self, name, content):
        return self._get_storage(name)._save(name, content)

    def delete(self, name):
        return self._get_storage(name).delete(name)

    def exists(self, name):
        return self._get_storage(name).exists(name)

    def url(self, name):
        return self._get_storage(name).url(name)

    def size(self, name):
        return self._get_storage(name).size(name)

    def get_valid_name(self, name):
        return self._get_storage(name).get_valid_name(name)

    def get_available_name(self, name, max_length=None):
        return self._get_storage(name).get_available_name(name, max_length=max_length)
