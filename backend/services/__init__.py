try:
    from .face_service import encode_faces_in_image, encode_selfie, find_matching_photos
except ImportError:
    # face_recognition not installed yet
    encode_faces_in_image = None
    encode_selfie = None
    find_matching_photos = None

from .upload_service import save_uploaded_photo, generate_thumbnail, apply_watermark, allowed_file
