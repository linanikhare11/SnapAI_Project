"""
Upload & Thumbnail Service
--------------------------
Handles file validation, saving, thumbnail generation,
and watermarking of event photos.
"""
import os
import uuid
import logging
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
THUMBNAIL_SIZE = (500, 500)


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_photo(file, upload_folder: str, event_id: int) -> dict:
    """
    Save an uploaded photo file to disk.
    Returns dict with filename, path, and original_name.
    """
    if not allowed_file(file.filename):
        raise ValueError(f"File type not allowed: {file.filename}")

    original_name = secure_filename(file.filename)
    ext = original_name.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    event_folder = os.path.join(upload_folder, f"event_{event_id}", "originals")
    os.makedirs(event_folder, exist_ok=True)

    save_path = os.path.join(event_folder, unique_name)
    file.save(save_path)

    file_size = os.path.getsize(save_path)
    return {
        'filename':      unique_name,
        'path':          save_path,
        'original_name': original_name,
        'file_size':     file_size
    }


def generate_thumbnail(original_path: str, upload_folder: str, event_id: int, filename: str) -> str:
    """
    Generate a compressed thumbnail for fast gallery loading.
    Returns the relative thumbnail path.
    """
    thumb_folder = os.path.join(upload_folder, f"event_{event_id}", "thumbnails")
    os.makedirs(thumb_folder, exist_ok=True)

    thumb_filename = f"thumb_{filename.rsplit('.', 1)[0]}.jpg"
    thumb_path = os.path.join(thumb_folder, thumb_filename)

    try:
        with Image.open(original_path) as img:
            img = img.convert('RGB')
            img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
            img.save(thumb_path, 'JPEG', quality=85, optimize=True)
        return thumb_path
    except Exception as e:
        logger.error(f"Thumbnail generation failed for {original_path}: {e}")
        return original_path


def apply_watermark(original_path: str, output_path: str, watermark_text: str, opacity: float = 0.35):
    """
    Apply a diagonal text watermark to a photo.
    """
    try:
        with Image.open(original_path) as base:
            base = base.convert('RGBA')
            width, height = base.size

            # Create transparent overlay
            overlay = Image.new('RGBA', base.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)

            # Font size relative to image
            font_size = max(30, int(min(width, height) * 0.04))
            try:
                # Cross-platform font loading
                import platform
                if platform.system() == 'Windows':
                    font_paths = [
                        os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'arial.ttf'),
                        os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'arial.ttf')
                    ]
                elif platform.system() == 'Darwin':
                    font_paths = [
                        '/Library/Fonts/Arial.ttf',
                        '/System/Library/Fonts/Helvetica.ttc'
                    ]
                else:  # Linux
                    font_paths = [
                        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
                    ]
                
                font = None
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        try:
                            font = ImageFont.truetype(font_path, font_size)
                            break
                        except Exception:
                            continue
                
                if font is None:
                    font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()

            # Tile the watermark diagonally
            import math
            text_w = font_size * len(watermark_text) * 0.6
            text_h = font_size * 1.5
            spacing_x = int(text_w * 2)
            spacing_y = int(text_h * 4)

            for x in range(-spacing_x, width + spacing_x, spacing_x):
                for y in range(-spacing_y, height + spacing_y, spacing_y):
                    draw.text(
                        (x, y),
                        watermark_text,
                        font=font,
                        fill=(255, 255, 255, int(255 * opacity))
                    )

            # Rotate overlay
            overlay_rotated = overlay.rotate(30, expand=False)
            watermarked = Image.alpha_composite(base, overlay_rotated).convert('RGB')
            watermarked.save(output_path, 'JPEG', quality=90)
    except Exception as e:
        logger.error(f"Watermark failed: {e}")
        # Fallback: just copy the file
        import shutil
        shutil.copy2(original_path, output_path)


def get_image_dimensions(path: str) -> tuple:
    try:
        with Image.open(path) as img:
            return img.size
    except Exception:
        return (0, 0)
