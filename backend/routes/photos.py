"""
Photo Routes — Upload, Indexing, Serving
All images are stored on Cloudinary; local disk is only used
as a temporary staging area for face-recognition processing.
"""
import os
import threading
import logging
import tempfile
from io import BytesIO
from flask import Blueprint, request, jsonify, send_file, current_app, make_response, redirect
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.database import db, Event, Photo, Photographer
from services.upload_service import allowed_file
from services.cloudinary_service import (
    upload_event_photo,
    upload_cover_photo,
    delete_cloudinary_asset,
    get_watermarked_url,
    get_thumbnail_url,
    download_to_temp,
)
import mimetypes
import cloudinary
import cloudinary.uploader

# Direct import of face_service (face_recognition is pre-loaded on app startup)
try:
    from services.face_service import encode_faces_in_image
    FACE_RECOGNITION_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Face recognition not available: {e}")
    encode_faces_in_image = None
    FACE_RECOGNITION_AVAILABLE = False

logger = logging.getLogger(__name__)
photos_bp = Blueprint('photos', __name__, url_prefix='/api/photos')


def _should_apply_watermark() -> bool:
    """Enable watermarking only when explicitly requested."""
    value = (request.args.get('wm') or '').strip().lower()
    return value in ('1', 'true', 'yes')


def _get_watermark_text(event_id: int) -> str:
    """Resolve watermark text from event photographer profile."""
    event = Event.query.get(event_id)
    if not event:
        return ''
    photographer = Photographer.query.get(event.photographer_id)
    if not photographer:
        return ''
    text = (photographer.watermark or photographer.name or '').strip()
    return text[:120]


# ─── Background Indexing Thread ────────────────────────────────────────────────

def index_event_photos(app, event_id: int):
    """
    Background thread: iterate all unprocessed photos in an event,
    download from Cloudinary, encode faces, and save results to DB.
    """
    tmp_files = []
    try:
        with app.app_context():
            if not FACE_RECOGNITION_AVAILABLE or encode_faces_in_image is None:
                logger.error(f"Face recognition not available for event {event_id}")
                event = Event.query.get(event_id)
                if event:
                    event.is_indexed = False
                    event.indexing_progress = 0
                    db.session.commit()
                return

            event = Event.query.get(event_id)
            if not event:
                logger.error(f"Event {event_id} not found during indexing")
                return

            photos = Photo.query.filter_by(event_id=event_id, is_processed=False).all()
            total  = len(photos)
            if total == 0:
                event.is_indexed = True
                event.indexing_progress = 100
                db.session.commit()
                logger.info(f"Event {event_id}: No photos to index")
                return

            model = 'hog'
            processed_count = 0

            for i, photo in enumerate(photos):
                tmp_path = None
                try:
                    # Try Cloudinary first, fallback to local disk
                    if photo.cloudinary_public_id:
                        tmp_path = download_to_temp(photo.cloudinary_public_id)
                        tmp_files.append(tmp_path)
                        path = tmp_path
                    else:
                        path = os.path.join(
                            current_app.config['UPLOAD_FOLDER'],
                            f"event_{event_id}", "originals", photo.filename
                        )

                    if not os.path.exists(path):
                        logger.warning(f"Photo file not found: {path}")
                        photo.is_processed = True
                        continue

                    encodings = encode_faces_in_image(path, model=model)
                    photo.set_face_encodings(encodings)
                    photo.face_count   = len(encodings)
                    photo.is_processed = True
                    processed_count += 1

                    progress = int(((i + 1) / total) * 100)
                    event.indexing_progress = progress
                    db.session.commit()

                except Exception as e:
                    logger.error(f"Failed to index photo {photo.id} ({photo.filename}): {e}")
                    photo.is_processed = True
                    try:
                        db.session.commit()
                    except Exception:
                        db.session.rollback()

            event.is_indexed = True
            event.indexing_progress = 100
            db.session.commit()
            logger.info(f"Indexing complete for event {event_id}: {processed_count}/{total} photos processed.")

    except Exception as e:
        logger.error(f"Critical error in indexing thread for event {event_id}: {e}", exc_info=True)
        try:
            with app.app_context():
                event = Event.query.get(event_id)
                if event:
                    event.is_indexed = False
                    event.indexing_progress = 0
                    db.session.commit()
        except Exception:
            pass
    finally:
        # Clean up temp files used for face-recognition
        for f in tmp_files:
            try:
                if f and os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass


# ─── Routes ─────────────────────────────────────────────────────────────────────

@photos_bp.route('/upload/<int:event_id>', methods=['POST'])
@jwt_required()
def upload_photos(event_id):
    photographer_id = int(get_jwt_identity())
    event = Event.query.filter_by(id=event_id, photographer_id=photographer_id).first_or_404()

    files = request.files.getlist('photos')
    if not files:
        return jsonify({'error': 'No files provided'}), 400

    uploaded = []
    errors   = []

    for file in files:
        if not file or not allowed_file(file.filename):
            errors.append(f"Skipped: {file.filename}")
            continue
        try:
            # Upload to Cloudinary
            result = upload_event_photo(file.stream, file.filename, event_id)

            photo = Photo(
                event_id=event_id,
                filename=result['filename'],
                original_name=result['original_name'],
                thumbnail_path=result['thumbnail_url'],
                cloudinary_url=result['url'],
                cloudinary_public_id=result['public_id'],
                file_size=result['file_size']
            )
            db.session.add(photo)
            db.session.flush()
            uploaded.append(result['filename'])

        except Exception as e:
            errors.append(f"Error with {file.filename}: {str(e)}")
            logger.error(f"Photo upload error for {file.filename}: {e}", exc_info=True)
            db.session.rollback()
            continue

    # Commit all successfully added photos
    try:
        db.session.commit()
    except Exception as e:
        logger.error(f"Database commit error: {e}")
        db.session.rollback()
        return jsonify({'error': f'Failed to save photos: {str(e)}', 'uploaded': uploaded, 'errors': errors}), 500

    # Reset indexing state when new photos arrive
    try:
        event.is_indexed = False
        event.indexing_progress = 0
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to reset indexing state: {e}")

    # AUTO-START indexing after successful uploads
    if uploaded:
        try:
            app = current_app._get_current_object()
            thread = threading.Thread(target=index_event_photos, args=(app, event_id), daemon=True)
            thread.start()
            logger.info(f"Auto-started indexing thread for event {event_id} with {len(uploaded)} photos")
        except Exception as e:
            logger.error(f"Failed to auto-start indexing: {e}", exc_info=True)

    return jsonify({
        'message':  f'{len(uploaded)} photo(s) uploaded to Cloudinary. Indexing started in background...',
        'uploaded': uploaded,
        'errors':   errors,
        'event':    event.to_dict()
    }), 201


@photos_bp.route('/index/<int:event_id>', methods=['POST'])
@jwt_required()
def start_indexing(event_id):
    photographer_id = int(get_jwt_identity())
    event = Event.query.filter_by(id=event_id, photographer_id=photographer_id).first_or_404()

    if event.is_indexed:
        return jsonify({'message': 'Already indexed'}), 200

    app = current_app._get_current_object()
    thread = threading.Thread(target=index_event_photos, args=(app, event_id), daemon=True)
    thread.start()

    return jsonify({'message': 'Indexing started in background', 'event': event.to_dict()}), 202


@photos_bp.route('/indexing-status/<int:event_id>', methods=['GET'])
@jwt_required()
def indexing_status(event_id):
    photographer_id = int(get_jwt_identity())
    event = Event.query.filter_by(id=event_id, photographer_id=photographer_id).first_or_404()
    return jsonify({
        'is_indexed':  event.is_indexed,
        'progress':    event.indexing_progress,
        'photo_count': event.photo_count()
    }), 200


@photos_bp.route('/list/<int:event_id>', methods=['GET'])
@jwt_required()
def list_photos(event_id):
    photographer_id = int(get_jwt_identity())
    event = Event.query.filter_by(id=event_id, photographer_id=photographer_id).first_or_404()

    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    pagination = Photo.query.filter_by(event_id=event_id)\
                            .order_by(Photo.uploaded_at.desc())\
                            .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'photos':    [p.to_dict() for p in pagination.items],
        'total':     pagination.total,
        'pages':     pagination.pages,
        'page':      page,
        'per_page':  per_page
    }), 200


@photos_bp.route('/delete/<int:photo_id>', methods=['DELETE'])
@jwt_required()
def delete_photo(photo_id):
    photographer_id = int(get_jwt_identity())
    photo = Photo.query.get_or_404(photo_id)
    event = Event.query.filter_by(id=photo.event_id, photographer_id=photographer_id).first_or_404()

    # Delete from Cloudinary
    if photo.cloudinary_public_id:
        delete_cloudinary_asset(photo.cloudinary_public_id)

    # Also remove any legacy local files if they exist
    upload_folder = current_app.config['UPLOAD_FOLDER']
    for path in [
        os.path.join(upload_folder, f"event_{photo.event_id}", "originals", photo.filename),
        photo.thumbnail_path if photo.thumbnail_path and not photo.thumbnail_path.startswith('http') else None
    ]:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    db.session.delete(photo)
    db.session.commit()
    return jsonify({'message': 'Photo deleted'}), 200


@photos_bp.route('/serve/<int:event_id>/<path:filename>')
def serve_photo(event_id, filename):
    """Serve original photos — redirects to Cloudinary URL if available."""
    # Try DB lookup first for Cloudinary URL
    photo = Photo.query.filter_by(event_id=event_id, filename=filename).first()

    if photo and photo.cloudinary_url:
        if _should_apply_watermark():
            wm_text = _get_watermark_text(event_id)
            if wm_text and photo.cloudinary_public_id:
                return redirect(get_watermarked_url(photo.cloudinary_public_id, wm_text))
        return redirect(photo.cloudinary_url)

    # Fallback: serve from local disk (legacy photos)
    upload_folder = current_app.config['UPLOAD_FOLDER']

    if filename.startswith('cover_'):
        file_path = os.path.join(upload_folder, f"event_{event_id}", "covers", filename)
    else:
        file_path = os.path.join(upload_folder, f"event_{event_id}", "originals", filename)

    if not os.path.exists(file_path):
        return jsonify({'error': 'Not found'}), 404

    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or 'image/jpeg'
    response = make_response(send_file(file_path, mimetype=mime_type, as_attachment=False))
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cache-Control'] = 'public, max-age=86400'
    return response


@photos_bp.route('/thumbnail/<int:event_id>/<path:filename>')
def serve_thumbnail(event_id, filename):
    """Serve thumbnail — redirects to Cloudinary transformation URL if available."""
    # Try DB lookup for Cloudinary public_id
    photo = Photo.query.filter_by(event_id=event_id, filename=filename).first()

    if photo and photo.cloudinary_public_id:
        if _should_apply_watermark():
            wm_text = _get_watermark_text(event_id)
            if wm_text:
                return redirect(get_watermarked_url(photo.cloudinary_public_id, wm_text))
        thumb_url = get_thumbnail_url(photo.cloudinary_public_id, 500, 500)
        return redirect(thumb_url)

    # Cloudinary thumbnail URL stored directly
    if photo and photo.thumbnail_path and photo.thumbnail_path.startswith('http'):
        return redirect(photo.thumbnail_path)

    # Fallback: local disk for legacy photos
    upload_folder = current_app.config['UPLOAD_FOLDER']

    if filename.startswith('cover_'):
        cover_path = os.path.join(upload_folder, f"event_{event_id}", "covers", filename)
        if os.path.exists(cover_path):
            response = make_response(send_file(cover_path, mimetype='image/jpeg'))
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Cache-Control'] = 'public, max-age=86400'
            return response
        return jsonify({'error': 'Not found'}), 404

    thumb_path = os.path.join(upload_folder, f"event_{event_id}", "thumbnails", f"thumb_{filename.rsplit('.', 1)[0]}.jpg")
    if not os.path.exists(thumb_path):
        orig_path = os.path.join(upload_folder, f"event_{event_id}", "originals", filename)
        if os.path.exists(orig_path):
            response = make_response(send_file(orig_path, mimetype='image/jpeg'))
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Cache-Control'] = 'public, max-age=86400'
            return response
        return jsonify({'error': 'Not found'}), 404

    response = make_response(send_file(thumb_path, mimetype='image/jpeg'))
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cache-Control'] = 'public, max-age=86400'
    return response


@photos_bp.route('/update/<int:event_id>/<int:photo_id>', methods=['POST'])
@jwt_required()
def update_photo(event_id, photo_id):
    """Update a photo with adjusted/cropped image — uploads to Cloudinary as cover."""
    logger.info(f"[PHOTOS] Update photo endpoint called: event_id={event_id}, photo_id={photo_id}")

    photographer_id = int(get_jwt_identity())
    event = Event.query.get(event_id)
    if not event or event.photographer_id != photographer_id:
        return jsonify({'error': 'Event not found or access denied'}), 404

    photo = Photo.query.filter_by(id=photo_id, event_id=event_id).first()
    if not photo:
        return jsonify({'error': 'Photo not found'}), 404

    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    try:
        result = upload_cover_photo(file.stream, file.filename, event_id, photo_id)

        # Update event cover_image — store Cloudinary URL for cover delivery
        event.cover_image = result['url']   # store full Cloudinary URL
        db.session.commit()

        logger.info(f"[PHOTOS] Cover uploaded to Cloudinary: {result['public_id']}")

        return jsonify({
            'success': True,
            'message': 'Photo adjusted and set as cover successfully',
            'cover_url': result['url'],
            'photo': {
                'id': photo.id,
                'filename': photo.filename,
                'event_id': photo.event_id
            }
        }), 200

    except Exception as e:
        logger.error(f"[PHOTOS] Error updating photo {photo_id}: {str(e)}", exc_info=True)
        return jsonify({'error': f'Update failed: {str(e)}'}), 500
