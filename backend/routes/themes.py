"""
Theme Routes — Theme Image Upload & Serving
"""
import os
import logging
from flask import Blueprint, request, jsonify, send_file, current_app, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.upload_service import allowed_file

logger = logging.getLogger(__name__)
themes_bp = Blueprint('themes', __name__, url_prefix='/api/themes')

# Valid event types
VALID_EVENT_TYPES = [
    'wedding',
    'birthday',
    'party',
    'general',
    'engagement',
    'farewell',
    'fresher',
    'diwali',
    'holi',
]


def _normalize_event_type(event_type):
    """Normalize event type from URL params/query strings."""
    return (event_type or '').strip().lower()


def _collect_theme_images(upload_folder, event_type):
    """Collect theme images from both supported folder names."""
    candidate_folders = [
        os.path.join(upload_folder, 'themes', event_type),
        os.path.join(upload_folder, 'theme', event_type),
    ]

    images = []
    chosen_folder = None

    for folder in candidate_folders:
        if not os.path.exists(folder):
            continue

        all_files = os.listdir(folder)
        valid_images = []
        for f in all_files:
            if '.' in f:
                ext = f.rsplit('.', 1)[1].lower()
                if ext in {'png', 'jpg', 'jpeg', 'webp', 'gif'}:
                    valid_images.append(f)

        if valid_images:
            chosen_folder = folder
            images = valid_images
            break

    return chosen_folder, images


@themes_bp.route('/upload/<event_type>', methods=['POST'])
@jwt_required()
def upload_theme_image(event_type):
    """Upload a theme image for a specific event type."""
    photographer_id = int(get_jwt_identity())
    event_type = _normalize_event_type(event_type)
    
    # Validate event type
    if event_type not in VALID_EVENT_TYPES:
        return jsonify({'error': f'Invalid event type. Must be one of: {", ".join(VALID_EVENT_TYPES)}'}), 400
    
    # Check file
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        themes_folder = os.path.join(upload_folder, 'themes', event_type)
        
        # Create themes folder if not exists
        os.makedirs(themes_folder, exist_ok=True)
        
        # Generate unique filename
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"theme_{photographer_id}_{int(os.urandom(4).hex(), 16)}.{file_ext}"
        filepath = os.path.join(themes_folder, filename)
        
        # Save file
        file.save(filepath)
        logger.info(f"[THEMES] Theme image uploaded: {filepath}")
        
        return jsonify({
            'message': 'Theme image uploaded successfully',
            'event_type': event_type,
            'filename': filename
        }), 201
        
    except Exception as e:
        logger.error(f"[THEMES] Error uploading theme: {str(e)}", exc_info=True)
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@themes_bp.route('/<event_type>', methods=['GET'])
def get_theme_image(event_type):
    """Get a theme image for an event type. Uses eventId parameter for deterministic selection."""
    event_type = _normalize_event_type(event_type)
    # Validate event type
    if event_type not in VALID_EVENT_TYPES:
        logger.warning(f"[THEMES] Invalid event type: {event_type}")
        return jsonify({'error': f'Invalid event type. Must be one of: {", ".join(VALID_EVENT_TYPES)}'}), 400
    
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        themes_folder, images = _collect_theme_images(upload_folder, event_type)

        # Fallback to general theme if event type folder has no images
        if not images and event_type != 'general':
            logger.warning(f"[THEMES] No images for {event_type}, falling back to general")
            themes_folder, images = _collect_theme_images(upload_folder, 'general')

        if not images:
            logger.warning(f"[THEMES] No theme images available for {event_type} or general")
            return jsonify({'error': f'No theme images available for {event_type}'}), 404
        
        # Use eventId from query parameter for deterministic selection
        # This ensures same event always gets same theme, but different events get different themes
        event_id = request.args.get('eventId', '0')
        try:
            event_id_int = int(event_id)
        except (ValueError, TypeError):
            event_id_int = 0
        
        # Use event_id to seed selection so same event always gets same image
        selected_image = images[event_id_int % len(images)]
        image_path = os.path.join(themes_folder, selected_image)
        
        logger.info(f"[THEMES] Serving theme image: {selected_image} for {event_type} (eventId={event_id})")
        
        response = make_response(send_file(image_path))
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache for 24 hours per unique eventId
        return response
        
    except Exception as e:
        logger.error(f"[THEMES] Error serving theme: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to fetch theme: {str(e)}'}), 500


@themes_bp.route('/list/<event_type>', methods=['GET'])
def list_theme_images(event_type):
    """List all available theme images for an event type."""
    event_type = _normalize_event_type(event_type)
    # Validate event type
    if event_type not in VALID_EVENT_TYPES:
        return jsonify({'error': f'Invalid event type. Must be one of: {", ".join(VALID_EVENT_TYPES)}'}), 400
    
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        themes_folder, images = _collect_theme_images(upload_folder, event_type)
        if not images:
            themes_folder, images = _collect_theme_images(upload_folder, 'general')
        
        return jsonify({
            'event_type': event_type,
            'count': len(images),
            'images': images,
            'source_folder': themes_folder
        }), 200
        
    except Exception as e:
        logger.error(f"[THEMES] Error listing themes: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to list themes: {str(e)}'}), 500
