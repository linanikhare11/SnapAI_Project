"""
Face Recognition Service
------------------------
Handles all face detection, encoding, and matching operations.
Uses the face_recognition library (built on dlib) under the hood.
"""
import face_recognition
import numpy as np
import json
import logging
from PIL import Image
import io

logger = logging.getLogger(__name__)


def encode_faces_in_image(image_path: str, model: str = 'cnn') -> list:
    """
    Detect all faces in an image and return their encodings.
    Returns a list of numpy arrays (one per face detected).
    """
    try:
        image = face_recognition.load_image_file(image_path)
        face_locations = face_recognition.face_locations(image, model=model)
        if not face_locations:
            return []
        encodings = face_recognition.face_encodings(image, face_locations)
        logger.info(f"Found {len(encodings)} face(s) in {image_path}")
        return encodings
    except Exception as e:
        logger.error(f"Error encoding faces in {image_path}: {e}")
        return []


def encode_selfie(image_bytes: bytes, model: str = 'hog') -> np.ndarray | None:
    """
    Encode a single selfie uploaded by a guest.
    OPTIMIZED: Use HOG model (CPU-friendly, fast).
    Returns a single encoding (the largest/most prominent face), or None.
    """
    try:
        # Force HOG model unless explicitly requesting CNN (and user has GPU)
        if model not in ['hog', 'cnn']:
            model = 'hog'
        
        image = face_recognition.load_image_file(io.BytesIO(image_bytes))
        face_locations = face_recognition.face_locations(image, model=model)
        if not face_locations:
            return None

        # Pick the largest face (by bounding box area)
        largest = max(
            face_locations,
            key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3])
        )
        encodings = face_recognition.face_encodings(image, [largest])
        return encodings[0] if encodings else None
    except Exception as e:
        logger.error(f"Error encoding selfie: {e}")
        return None


def find_matching_photos(
    selfie_encoding: np.ndarray,
    photos: list,          # list of Photo model objects
    tolerance: float = 0.38
) -> list:
    """
    Given a selfie encoding, scan all photos in an event and return
    those where a matching face is found.
    OPTIMIZED: Vectorized operations, minimal logging, efficient matching.

    photos: list of Photo ORM objects with get_face_encodings() method.
    Returns list of matching Photo objects.
    """
    matches = []
    
    # Ensure selfie_encoding is a proper 1D numpy array (shape: 128,)
    if not isinstance(selfie_encoding, np.ndarray):
        selfie_encoding = np.array(selfie_encoding, dtype=np.float64).flatten()
    else:
        selfie_encoding = np.array(selfie_encoding, dtype=np.float64).flatten()

    match_count = 0
    for photo in photos:
        try:
            stored_encodings = photo.get_face_encodings()
            if not stored_encodings:
                continue

            # Convert stored encodings (list of lists from JSON) to numpy array - vectorized
            try:
                known_encodings = np.array(stored_encodings, dtype=np.float64)
                # Validate shapes
                if known_encodings.ndim == 1:
                    known_encodings = known_encodings.reshape(1, -1)
                if known_encodings.shape[1] != 128:
                    continue
            except (ValueError, TypeError):
                continue
            
            # Perform face recognition comparison using face_distance - FAST
            distances = face_recognition.face_distance(known_encodings, selfie_encoding)
            
            # Check if any distance is below tolerance (match found)
            if np.min(distances) < tolerance:
                matches.append(photo)
                match_count += 1
        except Exception as e:
            logger.debug(f"Skipped photo {photo.id}: {type(e).__name__}")
            continue

    logger.info(f"Face match: found {match_count} photo(s) out of {len(photos)} scanned (tolerance={tolerance:.2f})")
    return matches


def count_faces_in_image(image_path: str, model: str = 'cnn') -> int:
    """Quick face count without full encoding — used for stats."""
    try:
        image = face_recognition.load_image_file(image_path)
        locations = face_recognition.face_locations(image, model=model)
        return len(locations)
    except Exception:
        return 0
