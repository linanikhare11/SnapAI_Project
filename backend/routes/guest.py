"""
Guest Routes — Public gallery access and AI face matching
"""
import os
import logging
import numpy as np
from flask import Blueprint, request, jsonify, current_app
from models.database import db, Event, Photo, Photographer

# Import face_service directly (face_recognition is pre-loaded on app startup)
try:
    from services.face_service import encode_selfie, find_matching_photos
    FACE_RECOGNITION_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Face recognition not available: {e}")
    encode_selfie = None
    find_matching_photos = None
    FACE_RECOGNITION_AVAILABLE = False

logger = logging.getLogger(__name__)
guest_bp = Blueprint('guest', __name__, url_prefix='/api/guest')


def verify_event_access(event: Event, pin: str | None) -> bool:
    if event.is_public:
        return True
    if pin and event.access_pin and pin == event.access_pin:
        return True
    return False


@guest_bp.route('/debug/events', methods=['GET'])
def debug_list_events():
    """DEBUG endpoint: List all events with their slugs."""
    try:
        all_events = Event.query.all()
        events_list = [{
            'id': e.id,
            'title': e.title,
            'slug': e.slug,
            'photographer_id': e.photographer_id,
            'is_public': e.is_public,
            'photo_count': len(e.photos)
        } for e in all_events]
        
        logger.info(f"[GUEST DEBUG] Listing {len(events_list)} events")
        return jsonify({
            'total_events': len(events_list),
            'events': events_list
        }), 200
    except Exception as e:
        logger.error(f"[GUEST DEBUG] Error listing events: {str(e)}")
        return jsonify({'error': str(e)}), 500


@guest_bp.route('/event/<slug>', methods=['GET'])
def get_public_event(slug):
    """Return event metadata for the guest landing page."""
    logger.info(f"[GUEST] get_public_event: slug={slug}")
    
    try:
        # Try exact slug match first
        event = Event.query.filter_by(slug=slug).first()
        
        if not event:
            logger.warning(f"[GUEST] Exact slug not found: {slug}")
            
            # Try partial slug match (in case of UUID mismatch)
            # Extract base slug without UUID suffix (last 6-char hex after last dash)
            import re
            base_slug = re.sub(r'-[a-f0-9]{6}$', '', slug)
            logger.info(f"[GUEST] Trying pattern match with base: {base_slug}")
            
            event = Event.query.filter(Event.slug.ilike(base_slug + '%')).first()
            
            if not event:
                logger.warning(f"[GUEST] Pattern match also failed for: {base_slug}")
                # Debug: List all slugs in database
                all_events = Event.query.all()
                logger.info(f"[GUEST] Available slugs in database: {[e.slug for e in all_events]}")
                return jsonify({'error': 'Event not found'}), 404
            
            logger.info(f"[GUEST] Found event with pattern match: {event.slug}")
        
        logger.info(f"[GUEST] Event found: event_id={event.id}, title={event.title}, slug={event.slug}")
        
        photographer = Photographer.query.get(event.photographer_id)
        if not photographer:
            logger.error(f"[GUEST] Photographer not found: photographer_id={event.photographer_id}")
            return jsonify({'error': 'Photographer not found'}), 500

        pin = request.args.get('pin')
        if not verify_event_access(event, pin):
            logger.warning(f"[GUEST] Access denied for event {event.slug} (requires PIN)")
            return jsonify({'error': 'Access denied. Please enter the correct PIN.', 'requires_pin': True}), 403

        response_data = {
            'event': event.to_dict(),
            'photographer': {
                'id':          photographer.id,
                'name':        photographer.name,
                'email':       photographer.email,
                'mobile_number': photographer.mobile_number,
                'logo_path':   photographer.logo_path,
                'brand_color': photographer.brand_color,
                'watermark':   photographer.watermark
            }
        }
        
        logger.info(f"[GUEST] Returning event data for {event.slug}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"[GUEST] Error in get_public_event: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@guest_bp.route('/event/<slug>/photos', methods=['GET'])
def get_event_photos(slug):
    """Paginated list of all photos for the gallery view."""
    event = Event.query.filter_by(slug=slug).first_or_404()

    pin  = request.args.get('pin')
    if not verify_event_access(event, pin):
        return jsonify({'error': 'Access denied', 'requires_pin': True}), 403

    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 48, type=int)

    pagination = Photo.query.filter_by(event_id=event.id)\
                            .order_by(Photo.uploaded_at.asc())\
                            .paginate(page=page, per_page=per_page, error_out=False)

    base_url = request.host_url.rstrip('/')
    photos_data = []
    for p in pagination.items:
        # Prefer Cloudinary URLs if available
        if p.cloudinary_public_id:
            from services.cloudinary_service import get_watermarked_url, get_thumbnail_url
            wm_url  = get_watermarked_url(p.cloudinary_public_id, '')
            thm_url = get_thumbnail_url(p.cloudinary_public_id, 500, 500)
            photos_data.append({
                'id':        p.id,
                'filename':  p.filename,
                'thumb_url': thm_url,
                'full_url':  p.cloudinary_url or wm_url,
            })
        else:
            photos_data.append({
                'id':        p.id,
                'filename':  p.filename,
                'thumb_url': f"{base_url}/api/photos/thumbnail/{event.id}/{p.filename}?wm=1",
                'full_url':  f"{base_url}/api/photos/serve/{event.id}/{p.filename}?wm=1",
            })

    return jsonify({
        'photos':   photos_data,
        'total':    pagination.total,
        'pages':    pagination.pages,
        'page':     page,
        'per_page': per_page
    }), 200


@guest_bp.route('/event/<slug>/find-me', methods=['POST'])
def find_my_photos(slug):
    """
    AI Face Match endpoint.
    Accepts a selfie upload and returns photos where the person appears.
    OPTIMIZED: Uses HOG model for fast matching, vectorized operations.
    """
    import time
    start_time = time.time()
    
    try:
        if not FACE_RECOGNITION_AVAILABLE or encode_selfie is None or find_matching_photos is None:
            logger.error(f"[FIND-ME] Face matching not available")
            return jsonify({
                'error': 'Face matching service unavailable. Face recognition library not properly installed.'
            }), 503
        
        event = Event.query.filter_by(slug=slug).first_or_404()
        logger.info(f"[FIND-ME] Request started for event {event.id} ({event.title})")

        pin = request.form.get('pin') or request.args.get('pin')
        if not verify_event_access(event, pin):
            return jsonify({'error': 'Access denied', 'requires_pin': True}), 403

        if not event.is_indexed:
            return jsonify({
                'error': 'This event gallery is still being indexed by AI. Please try again shortly.',
                'indexing_progress': event.indexing_progress
            }), 503

        if 'selfie' not in request.files:
            return jsonify({'error': 'Selfie image is required'}), 400

        selfie_file = request.files['selfie']
        if not selfie_file.filename:
            return jsonify({'error': 'No file selected'}), 400

        selfie_bytes = selfie_file.read()
        
        if not selfie_bytes:
            return jsonify({'error': 'Selfie file is empty'}), 400

        # Consent check
        consent = request.form.get('consent', 'false').lower()
        if consent != 'true':
            return jsonify({'error': 'Consent is required to use face recognition'}), 400

        # Encode selfie with HOG model (fast, CPU-friendly)
        t_encode_start = time.time()
        logger.info(f"[FIND-ME] Encoding selfie from file: {selfie_file.filename}")
        selfie_encoding = encode_selfie(
            selfie_bytes,
            model='hog'  # Force HOG model (fast CPU-friendly)
        )
        t_encode_time = time.time() - t_encode_start
        logger.info(f"[FIND-ME] Selfie encoded in {t_encode_time:.2f}s")

        if selfie_encoding is None:
            logger.warning(f"[FIND-ME] No face detected in selfie for event {event.id}")
            return jsonify({
                'error': 'No face detected in your selfie. Please upload a clear, well-lit photo facing the camera.'
            }), 422

        # Get all processed photos
        t_query_start = time.time()
        all_photos = Photo.query.filter_by(event_id=event.id, is_processed=True).all()
        t_query_time = time.time() - t_query_start
        logger.info(f"[FIND-ME] Loaded {len(all_photos)} photos from DB in {t_query_time:.2f}s")
        
        if not all_photos:
            logger.warning(f"[FIND-ME] No indexed photos found for event {event.id}")
            return jsonify({'error': 'No indexed photos found for this event.'}), 404

        logger.info(f"[FIND-ME] Starting scan of {len(all_photos)} photos for matches...")

        # Use HOG-optimized tolerance (slightly higher for HOG model accuracy)
        tolerance = 0.38  # Optimized for HOG model
        t_match_start = time.time()
        matched = find_matching_photos(selfie_encoding, all_photos, tolerance=tolerance)
        t_match_time = time.time() - t_match_start
        logger.info(f"[FIND-ME] Matching completed in {t_match_time:.2f}s, found {len(matched)} matches")

        base_url = request.host_url.rstrip('/')
        results = []
        for p in matched:
            # Prefer Cloudinary URLs if available
            if p.cloudinary_public_id:
                from services.cloudinary_service import get_thumbnail_url
                thm_url = get_thumbnail_url(p.cloudinary_public_id, 500, 500)
                results.append({
                    'id':        p.id,
                    'filename':  p.filename,
                    'thumb_url': thm_url,
                    'full_url':  p.cloudinary_url or thm_url,
                })
            else:
                results.append({
                    'id':       p.id,
                    'filename': p.filename,
                    'thumb_url': f"{base_url}/api/photos/thumbnail/{event.id}/{p.filename}?wm=1",
                    'full_url':  f"{base_url}/api/photos/serve/{event.id}/{p.filename}?wm=1",
                })

        total_time = time.time() - start_time
        logger.info(f"[FIND-ME] ✓ Complete! Found {len(results)}/{len(all_photos)} matches in {total_time:.2f}s total")

        return jsonify({
            'matched':       len(results),
            'total_scanned': len(all_photos),
            'photos':        results,
            'processing_time_ms': int(total_time * 1000)
        }), 200
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"[FIND-ME] Error after {total_time:.2f}s: {type(e).__name__}: {e}", exc_info=True)
        return jsonify({
            'error': 'An unexpected error occurred while processing your request. Please try again.',
            'detail': str(e) if current_app.debug else None,
            'elapsed_time_ms': int(total_time * 1000)
        }), 500


@guest_bp.route('/verify-pin', methods=['POST'])
def verify_pin():
    data  = request.get_json()
    slug  = data.get('slug')
    pin   = data.get('pin')

    if not slug or not pin:
        return jsonify({'error': 'slug and pin required'}), 400

    event = Event.query.filter_by(slug=slug).first_or_404()

    if event.is_public or (event.access_pin and event.access_pin == pin):
        return jsonify({'success': True}), 200
    return jsonify({'error': 'Incorrect PIN'}), 403
