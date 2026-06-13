"""
Photographer Profile Routes — Contact Info & Portfolio Management
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.database import db, Photographer, Photo, Event
from services.upload_service import save_uploaded_photo, generate_thumbnail, allowed_file
import json
from datetime import datetime

profile_bp = Blueprint('profile', __name__, url_prefix='/api/profile')


@profile_bp.route('/me', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current photographer's profile with all details."""
    photographer_id = int(get_jwt_identity())
    photographer = Photographer.query.get_or_404(photographer_id)
    return jsonify(photographer.to_dict()), 200


@profile_bp.route('/me/contact', methods=['PUT'])
@jwt_required()
def update_contact_info():
    """Update photographer contact information."""
    photographer_id = int(get_jwt_identity())
    photographer = Photographer.query.get_or_404(photographer_id)
    data = request.get_json()

    # Update allowed fields
    if 'name' in data:
        photographer.name = data['name']
    if 'mobile_number' in data:
        photographer.mobile_number = data['mobile_number']
    if 'email' in data:
        # Check if new email is unique
        existing = Photographer.query.filter_by(email=data['email']).first()
        if existing and existing.id != photographer_id:
            return jsonify({'error': 'Email already in use'}), 409
        photographer.email = data['email']

    db.session.commit()
    return jsonify({
        'message': 'Contact info updated',
        'photographer': photographer.to_dict()
    }), 200


@profile_bp.route('/me/about', methods=['PUT'])
@jwt_required()
def update_about_photographer():
    """Update About Photographer section (Contact display)."""
    photographer_id = int(get_jwt_identity())
    photographer = Photographer.query.get_or_404(photographer_id)
    data = request.get_json()

    # These fields are displayed in "About Photographer" section
    if 'name' in data:
        photographer.name = data['name']
    if 'mobile_number' in data:
        photographer.mobile_number = data['mobile_number']
    if 'email' in data:
        photographer.email = data['email']

    db.session.commit()
    return jsonify({
        'message': 'About photographer updated',
        'photographer': photographer.to_dict()
    }), 200


@profile_bp.route('/me/photography', methods=['PUT'])
@jwt_required()
def update_photography_section():
    """
    Update Photography section details:
    - Specializations (Wedding, Birthday, Party, Events, etc.)
    - Services description
    - Technologies description
    """
    photographer_id = int(get_jwt_identity())
    photographer = Photographer.query.get_or_404(photographer_id)
    data = request.get_json()

    if 'specializations' in data:
        photographer.set_specializations(data['specializations'])
    if 'services' in data:
        photographer.services = data['services']
    if 'technologies' in data:
        photographer.technologies = data['technologies']

    db.session.commit()
    return jsonify({
        'message': 'Photography section updated',
        'photographer': photographer.to_dict()
    }), 200


@profile_bp.route('/me/special-photos', methods=['GET'])
@jwt_required()
def get_special_photos():
    """Get photographer's special/portfolio photos."""
    photographer_id = int(get_jwt_identity())
    photographer = Photographer.query.get_or_404(photographer_id)
    
    special_photo_ids = photographer.get_special_photos()
    
    # Fetch photo details
    photos = []
    for photo_id in special_photo_ids:
        photo = Photo.query.get(photo_id)
        if photo:
            photos.append(photo.to_dict())
    
    return jsonify({
        'special_photos': photos
    }), 200


@profile_bp.route('/me/photos', methods=['GET'])
@jwt_required()
def list_my_photos_for_portfolio():
    """List all photos owned by this photographer for portfolio selection."""
    photographer_id = int(get_jwt_identity())

    photos = (
        Photo.query
        .join(Event, Photo.event_id == Event.id)
        .filter(Event.photographer_id == photographer_id)
        .order_by(Photo.uploaded_at.desc())
        .all()
    )

    return jsonify({
        'photos': [p.to_dict() for p in photos],
        'count': len(photos)
    }), 200


@profile_bp.route('/me/special-photos/upload', methods=['POST'])
@jwt_required()
def upload_special_photos():
    """Upload photos directly for portfolio without requiring event selection."""
    photographer_id = int(get_jwt_identity())
    photographer = Photographer.query.get_or_404(photographer_id)

    files = request.files.getlist('photos')
    if not files:
        return jsonify({'error': 'No files provided'}), 400

    # Create or reuse a private portfolio event for this photographer
    portfolio_slug = f'portfolio-{photographer_id}'
    portfolio_event = Event.query.filter_by(slug=portfolio_slug).first()
    if not portfolio_event:
        portfolio_event = Event(
            photographer_id=photographer_id,
            title='Portfolio Uploads',
            description='Auto-created event for profile portfolio uploads',
            slug=portfolio_slug,
            event_type='general',
            is_public=False,
            is_indexed=False,
            indexing_progress=0
        )
        db.session.add(portfolio_event)
        db.session.flush()

    upload_folder = current_app.config['UPLOAD_FOLDER']
    uploaded_photos = []
    special_photo_ids = photographer.get_special_photos()

    for file in files:
        if not file or not allowed_file(file.filename):
            continue

        saved = save_uploaded_photo(file, upload_folder, portfolio_event.id)
        thumb = generate_thumbnail(saved['path'], upload_folder, portfolio_event.id, saved['filename'])

        photo = Photo(
            event_id=portfolio_event.id,
            filename=saved['filename'],
            original_name=saved['original_name'],
            thumbnail_path=thumb,
            file_size=saved['file_size'],
            is_processed=False
        )
        db.session.add(photo)
        db.session.flush()

        uploaded_photos.append(photo.to_dict())
        if photo.id not in special_photo_ids:
            special_photo_ids.append(photo.id)

    photographer.set_special_photos(special_photo_ids)
    db.session.commit()

    return jsonify({
        'message': f'{len(uploaded_photos)} photo(s) uploaded to portfolio',
        'uploaded_photos': uploaded_photos,
        'special_photos': photographer.get_special_photos()
    }), 201


@profile_bp.route('/me/special-photos', methods=['POST'])
@jwt_required()
def add_special_photo():
    """Add a photo to special/portfolio photos."""
    photographer_id = int(get_jwt_identity())
    photographer = Photographer.query.get_or_404(photographer_id)
    data = request.get_json()

    photo_id = data.get('photo_id')
    if not photo_id:
        return jsonify({'error': 'photo_id is required'}), 400

    # Verify photo belongs to this photographer
    photo = Photo.query.get_or_404(photo_id)
    event = photo.event
    if event.photographer_id != photographer_id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Add to special photos if not already there
    special_photos = photographer.get_special_photos()
    if photo_id not in special_photos:
        special_photos.append(photo_id)
        photographer.set_special_photos(special_photos)
        db.session.commit()

    return jsonify({
        'message': 'Photo added to portfolio',
        'special_photos': photographer.get_special_photos()
    }), 201


@profile_bp.route('/me/special-photos/<int:photo_id>', methods=['DELETE'])
@jwt_required()
def remove_special_photo(photo_id):
    """Remove a photo from special/portfolio photos."""
    photographer_id = int(get_jwt_identity())
    photographer = Photographer.query.get_or_404(photographer_id)

    # Verify photo belongs to this photographer
    photo = Photo.query.get_or_404(photo_id)
    event = photo.event
    if event.photographer_id != photographer_id:
        return jsonify({'error': 'Unauthorized'}), 403

    special_photos = photographer.get_special_photos()
    if photo_id in special_photos:
        special_photos.remove(photo_id)
        photographer.set_special_photos(special_photos)
        db.session.commit()

    return jsonify({
        'message': 'Photo removed from portfolio',
        'special_photos': photographer.get_special_photos()
    }), 200


@profile_bp.route('/me/chat', methods=['GET'])
@jwt_required()
def get_profile_chat_messages():
    """Get LN profile chat messages for current photographer."""
    photographer_id = int(get_jwt_identity())
    photographer = Photographer.query.get_or_404(photographer_id)

    messages = photographer.get_profile_chat_messages()
    return jsonify({'messages': messages}), 200


@profile_bp.route('/me/chat', methods=['POST'])
@jwt_required()
def add_profile_chat_message():
    """Add a photographer/client chat message in profile chat."""
    photographer_id = int(get_jwt_identity())
    photographer = Photographer.query.get_or_404(photographer_id)
    data = request.get_json() or {}

    message = (data.get('message') or '').strip()
    sender = (data.get('sender') or 'photographer').strip().lower()
    if not message:
        return jsonify({'error': 'message is required'}), 400
    if sender not in {'photographer', 'client'}:
        return jsonify({'error': 'sender must be photographer or client'}), 400

    now_iso = datetime.utcnow().isoformat()
    messages = photographer.get_profile_chat_messages()

    chat_message = {
        'role': sender,
        'text': message,
        'created_at': now_iso
    }
    messages.append(chat_message)

    photographer.set_profile_chat_messages(messages[-200:])
    db.session.commit()

    return jsonify({
        'message': 'Chat updated',
        'messages': photographer.get_profile_chat_messages()
    }), 201


@profile_bp.route('/<int:photographer_id>', methods=['GET'])
def get_photographer_public_profile(photographer_id):
    """Get public photographer profile (visible to all users)."""
    import logging
    logger = logging.getLogger(__name__)
    
    photographer = Photographer.query.get_or_404(photographer_id)
    logger.info(f'[PUBLIC-PROFILE] Fetching profile for photographer ID: {photographer_id} ({photographer.name})')
    
    # Return only public-facing information
    profile = photographer.to_dict()
    
    # Get special photos with their details
    special_photo_ids = photographer.get_special_photos()
    logger.info(f'[PUBLIC-PROFILE] Special photo IDs: {special_photo_ids}')
    
    special_photos = []
    for photo_id in special_photo_ids:
        photo = Photo.query.get(photo_id)
        if photo:
            logger.info(f'[PUBLIC-PROFILE] Found photo ID {photo_id}: {photo.filename}')
            special_photos.append(photo.to_dict())
        else:
            logger.warning(f'[PUBLIC-PROFILE] Photo ID {photo_id} NOT FOUND in database')
    
    logger.info(f'[PUBLIC-PROFILE] Returning {len(special_photos)} featured photos')
    profile['special_photos_details'] = special_photos
    
    return jsonify(profile), 200
