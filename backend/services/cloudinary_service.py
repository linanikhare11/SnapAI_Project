"""
Cloudinary Service
------------------
Handles all image upload, delivery (thumbnails, watermarks),
and deletion using Cloudinary as the primary storage backend.

Cloudinary public_id convention:
  snapai/event_{event_id}/originals/{uuid}
  snapai/event_{event_id}/covers/{filename}
  snapai/logos/{photographer_id}
  snapai/portfolio/{photographer_id}/{uuid}
"""

import os
import uuid
import logging
import tempfile
from io import BytesIO

import cloudinary
import cloudinary.uploader
import cloudinary.api

logger = logging.getLogger(__name__)


def init_cloudinary(app):
    """Configure Cloudinary with credentials from Flask app config."""
    cloudinary.config(
        cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
        api_key=app.config['CLOUDINARY_API_KEY'],
        api_secret=app.config['CLOUDINARY_API_SECRET'],
        secure=True
    )
    logger.info("[CLOUDINARY] Cloudinary configured: cloud=%s", app.config['CLOUDINARY_CLOUD_NAME'])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_public_id(folder: str, filename: str) -> str:
    """Strip file extension for Cloudinary public_id (Cloudinary stores format separately)."""
    name = os.path.splitext(filename)[0]
    return f"{folder}/{name}"


# ── Upload Functions ───────────────────────────────────────────────────────────

def upload_event_photo(file_stream, filename: str, event_id: int) -> dict:
    """
    Upload an original event photo to Cloudinary.

    Returns:
        {
          'public_id': str,       # Cloudinary asset ID (for deletion)
          'url': str,             # Secure delivery URL
          'thumbnail_url': str,   # Auto-generated thumbnail URL via transformation
          'filename': str,        # UUID filename stored in DB
          'original_name': str,   # Original upload filename
          'file_size': int,       # Bytes
        }
    """
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    public_id = _build_public_id(f"snapai/event_{event_id}/originals", unique_name)

    # Read bytes to get file size
    data = file_stream.read()
    file_size = len(data)

    logger.info("[CLOUDINARY] Uploading photo: %s (%.1f KB)", unique_name, file_size / 1024)

    result = cloudinary.uploader.upload(
        BytesIO(data),
        public_id=public_id,
        resource_type='image',
        overwrite=False,
        quality='auto',
        fetch_format='auto',
    )

    secure_url = result['secure_url']

    # Build thumbnail URL using Cloudinary's on-the-fly transformation
    thumbnail_url = cloudinary.CloudinaryImage(result['public_id']).build_url(
        width=500,
        height=500,
        crop='limit',
        quality='auto',
        fetch_format='auto',
        secure=True
    )

    logger.info("[CLOUDINARY] ✓ Photo uploaded: %s", result['public_id'])

    return {
        'public_id':     result['public_id'],
        'url':           secure_url,
        'thumbnail_url': thumbnail_url,
        'filename':      unique_name,
        'original_name': filename,
        'file_size':     file_size,
    }


def upload_cover_photo(file_stream, filename: str, event_id: int, photo_id: int) -> dict:
    """
    Upload an adjusted cover photo to Cloudinary.

    Returns:
        {
          'public_id': str,
          'url': str,
          'cover_filename': str,   # e.g. cover_photo_{id}.jpg (for DB compat)
        }
    """
    cover_filename = f"cover_photo_{photo_id}.jpg"
    public_id = _build_public_id(f"snapai/event_{event_id}/covers", cover_filename)

    data = file_stream.read() if hasattr(file_stream, 'read') else file_stream

    logger.info("[CLOUDINARY] Uploading cover: %s", cover_filename)

    result = cloudinary.uploader.upload(
        BytesIO(data),
        public_id=public_id,
        resource_type='image',
        overwrite=True,
        quality='auto',
        fetch_format='auto',
    )

    logger.info("[CLOUDINARY] ✓ Cover uploaded: %s", result['public_id'])

    return {
        'public_id':      result['public_id'],
        'url':            result['secure_url'],
        'cover_filename': cover_filename,
    }


def upload_logo(file_stream, filename: str, photographer_id: int) -> dict:
    """
    Upload a photographer logo/profile image to Cloudinary.

    Returns:
        {
          'public_id': str,
          'url': str,
          'logo_filename': str,
        }
    """
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    logo_filename = f"logo_{photographer_id}.{ext}"
    public_id = f"snapai/logos/{logo_filename.rsplit('.', 1)[0]}"

    data = file_stream.read()

    logger.info("[CLOUDINARY] Uploading logo for photographer %d", photographer_id)

    result = cloudinary.uploader.upload(
        BytesIO(data),
        public_id=public_id,
        resource_type='image',
        overwrite=True,
        quality='auto',
        fetch_format='auto',
        transformation=[
            {'width': 400, 'height': 400, 'crop': 'limit'}
        ]
    )

    logger.info("[CLOUDINARY] ✓ Logo uploaded: %s", result['public_id'])

    return {
        'public_id':    result['public_id'],
        'url':          result['secure_url'],
        'logo_filename': logo_filename,
    }


def upload_portfolio_photo(file_stream, filename: str, photographer_id: int) -> dict:
    """
    Upload a portfolio/special photo for a photographer's profile.

    Returns:
        {
          'public_id': str,
          'url': str,
          'thumbnail_url': str,
          'filename': str,
          'original_name': str,
          'file_size': int,
        }
    """
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    public_id = _build_public_id(f"snapai/portfolio/{photographer_id}", unique_name)

    data = file_stream.read()
    file_size = len(data)

    logger.info("[CLOUDINARY] Uploading portfolio photo for photographer %d", photographer_id)

    result = cloudinary.uploader.upload(
        BytesIO(data),
        public_id=public_id,
        resource_type='image',
        overwrite=False,
        quality='auto',
        fetch_format='auto',
    )

    thumbnail_url = cloudinary.CloudinaryImage(result['public_id']).build_url(
        width=500,
        height=500,
        crop='limit',
        quality='auto',
        fetch_format='auto',
        secure=True
    )

    logger.info("[CLOUDINARY] ✓ Portfolio photo uploaded: %s", result['public_id'])

    return {
        'public_id':     result['public_id'],
        'url':           result['secure_url'],
        'thumbnail_url': thumbnail_url,
        'filename':      unique_name,
        'original_name': filename,
        'file_size':     file_size,
    }


# ── Deletion ───────────────────────────────────────────────────────────────────

def delete_cloudinary_asset(public_id: str) -> bool:
    """
    Delete an asset from Cloudinary by public_id.
    Returns True on success, False on error.
    """
    if not public_id:
        return False
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type='image')
        success = result.get('result') in ('ok', 'not found')
        if success:
            logger.info("[CLOUDINARY] ✓ Deleted asset: %s", public_id)
        else:
            logger.warning("[CLOUDINARY] Unexpected destroy result for %s: %s", public_id, result)
        return success
    except Exception as e:
        logger.error("[CLOUDINARY] Failed to delete %s: %s", public_id, e)
        return False


# ── URL Helpers ────────────────────────────────────────────────────────────────

def get_watermarked_url(public_id: str, watermark_text: str) -> str:
    """
    Return a Cloudinary URL with text watermark overlay applied.
    Uses Cloudinary's native text overlay transformation.
    """
    if not watermark_text or not public_id:
        return cloudinary.CloudinaryImage(public_id).build_url(secure=True)

    return cloudinary.CloudinaryImage(public_id).build_url(
        transformation=[
            {
                'overlay': {
                    'font_family': 'Arial',
                    'font_size': 36,
                    'font_weight': 'bold',
                    'text': watermark_text,
                },
                'color': '#FFFFFF',
                'opacity': 40,
                'gravity': 'south_east',
                'x': 20,
                'y': 20,
            }
        ],
        quality='auto',
        fetch_format='auto',
        secure=True
    )


def get_thumbnail_url(public_id: str, width: int = 500, height: int = 500) -> str:
    """Return a Cloudinary thumbnail URL for a given public_id."""
    return cloudinary.CloudinaryImage(public_id).build_url(
        width=width,
        height=height,
        crop='limit',
        quality='auto',
        fetch_format='auto',
        secure=True
    )


def download_to_temp(public_id: str) -> str:
    """
    Download a Cloudinary asset to a local temp file.
    Used by face-recognition (which needs a local file path).
    Returns the local temp file path.
    """
    import urllib.request
    url = cloudinary.CloudinaryImage(public_id).build_url(secure=True)
    suffix = '.' + public_id.rsplit('.', 1)[-1] if '.' in public_id.split('/')[-1] else '.jpg'
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    urllib.request.urlretrieve(url, tmp_path)
    return tmp_path
