import io
import os
import uuid
import logging
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """
    Extract the client IP address safely from the request.
    Only trust HTTP_X_FORWARDED_FOR if explicitly configured (e.g. on Render/reverse proxy).
    """
    if os.getenv('RENDER_EXTERNAL_HOSTNAME') or os.getenv('TRUST_PROXY_HEADERS'):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def process_avatar_image(uploaded_file, max_dimension=400, quality=85):
    """
    Optimizes, auto-orients, square-crops, and compresses an uploaded avatar image.
    Transforms raw smartphone/camera photos (up to 10MB) into a crisp, high-DPI
    lightweight (~15KB-35KB) baseline JPEG for instant rendering without progressive scan lag.
    Returns: (ContentFile, str_filename)
    """
    try:
        if hasattr(uploaded_file, 'seek'):
            uploaded_file.seek(0)

        img = Image.open(uploaded_file)

        # 1. Auto-orient based on EXIF metadata (fixes sideways phone photos)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # 2. Normalize color mode to RGB (handles RGBA / transparent PNGs / Paletted)
        if img.mode in ('RGBA', 'LA', 'P'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if 'A' in img.getbands():
                bg.paste(img, mask=img.split()[-1])
            else:
                bg.paste(img)
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # 3. Center crop to a 1:1 square aspect ratio
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        right = left + min_dim
        bottom = top + min_dim
        img = img.crop((left, top, right, bottom))

        # 4. Downscale to max_dimension (400x400) using high-quality Lanczos resampling
        if min_dim > max_dimension:
            img = img.resize((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        # 5. Export as baseline non-progressive JPEG for instant 1-frame rendering
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True, progressive=False)
        buffer.seek(0)

        filename = f"avatar_{uuid.uuid4().hex[:12]}.jpg"
        return ContentFile(buffer.getvalue(), name=filename), filename
    except Exception as e:
        logger.error(f"Failed to process avatar image: {e}")
        raise ValidationError("Invalid or corrupted image format. Please upload a valid JPG, PNG, or WEBP image.")

