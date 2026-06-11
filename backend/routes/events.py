"""
Event Routes — CRUD for Events (Photographer Dashboard)
"""

import re
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.database import db, Photographer, Event, Photo

events_bp = Blueprint('events', __name__, url_prefix='/api/events')


# ── Helper: Slug Generator ─────────────────────────
def slugify(text: str) -> str:
    """Generate a unique slug from text."""
    base_slug = text.lower().strip()
    base_slug = re.sub(r'[^\w\s-]', '', base_slug)
    base_slug = re.sub(r'[\s_-]+', '-', base_slug)
    base_slug = re.sub(r'^-+|-+$', '', base_slug)
    
    # Add UUID suffix to ensure uniqueness
    unique_suffix = uuid.uuid4().hex[:6]
    slug = f"{base_slug}-{unique_suffix}"
    
    # Verify uniqueness in database
    existing = Event.query.filter_by(slug=slug).first()
    if existing:
        # If collision (very unlikely), add another UUID
        unique_suffix2 = uuid.uuid4().hex[:6]
        slug = f"{base_slug}-{unique_suffix}-{unique_suffix2}"
    
    print(f"[DEBUG] slugify: '{text}' -> '{slug}'")
    return slug


# ── LIST EVENTS ────────────────────────────────────
@events_bp.route('/', methods=['GET'])
@jwt_required()
def list_events():
    try:
        photographer_id = int(get_jwt_identity())
        print(f"[DEBUG] LIST_EVENTS: photographer_id={photographer_id}")

        events = Event.query.filter_by(
            photographer_id=photographer_id
        ).order_by(Event.created_at.desc()).all()

        print(f"[DEBUG] LIST_EVENTS: found {len(events)} events")
        result = [e.to_dict() for e in events]
        print(f"[DEBUG] LIST_EVENTS: returning {result}")

        return jsonify(result), 200

    except Exception as e:
        print("LIST EVENTS ERROR:", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to fetch events'}), 500


# ── CREATE EVENT (FIXED) ───────────────────────────
@events_bp.route('/', methods=['POST'])
@jwt_required()
def create_event():
    try:
        photographer_id = int(get_jwt_identity())
        print(f"[DEBUG] CREATE_EVENT: photographer_id={photographer_id}")

        data = request.get_json()
        print(f"[DEBUG] CREATE_EVENT: data={data}")

        # 🔥 Fix: Handle missing JSON
        if not data:
            print("[DEBUG] CREATE_EVENT: No JSON data received")
            return jsonify({'error': 'Invalid or missing JSON body'}), 400

        # 🔥 Fix: Required field validation
        if not data.get('title'):
            print("[DEBUG] CREATE_EVENT: Title is missing")
            return jsonify({'error': 'Title is required'}), 400

        # 🔥 Fix: Safe date parsing
        event_date = None
        if data.get('event_date'):
            try:
                print(f"[DEBUG] CREATE_EVENT: Parsing date: {data['event_date']}")
                event_date = datetime.strptime(data['event_date'], "%Y-%m-%d")
                print(f"[DEBUG] CREATE_EVENT: Date parsed: {event_date}")
            except ValueError as ve:
                print(f"[DEBUG] CREATE_EVENT: Date parsing failed: {ve}")
                return jsonify({'error': 'Invalid date format (YYYY-MM-DD required)'}), 400

        print(f"[DEBUG] CREATE_EVENT: Creating event with title={data['title']}")
        event = Event(
            photographer_id=photographer_id,
            title=data['title'],
            description=data.get('description'),
            event_date=event_date,
            slug=slugify(data['title']),
            event_type=data.get('event_type', 'general'),  # NEW: Support event_type
            is_public=data.get('is_public', True),
            access_pin=data.get('access_pin')
        )

        db.session.add(event)
        db.session.commit()
        
        print(f"[DEBUG] CREATE_EVENT: Event created successfully with ID={event.id}")

        return jsonify({
            'message': 'Event created successfully',
            'event': event.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        print("CREATE EVENT ERROR:", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ── GET EVENT ──────────────────────────────────────
@events_bp.route('/<int:event_id>', methods=['GET'])
@jwt_required()
def get_event(event_id):
    try:
        photographer_id = int(get_jwt_identity())

        event = Event.query.filter_by(
            id=event_id,
            photographer_id=photographer_id
        ).first_or_404()

        return jsonify(event.to_dict()), 200

    except Exception as e:
        print("GET EVENT ERROR:", str(e))
        return jsonify({'error': 'Event not found'}), 404


# ── UPDATE EVENT ───────────────────────────────────
@events_bp.route('/<int:event_id>', methods=['PUT'])
@jwt_required()
def update_event(event_id):
    try:
        photographer_id = int(get_jwt_identity())

        event = Event.query.filter_by(
            id=event_id,
            photographer_id=photographer_id
        ).first_or_404()

        data = request.get_json()

        if not data:
            return jsonify({'error': 'Invalid JSON body'}), 400

        # Safe update fields
        if 'title' in data:
            event.title = data['title']

        if 'description' in data:
            event.description = data['description']

        if 'event_date' in data:
            try:
                event.event_date = datetime.strptime(data['event_date'], "%Y-%m-%d")
            except ValueError:
                return jsonify({'error': 'Invalid date format (YYYY-MM-DD required)'}), 400

        if 'is_public' in data:
            event.is_public = data['is_public']

        if 'access_pin' in data:
            event.access_pin = data['access_pin']

        if 'event_type' in data:
            event.event_type = data['event_type']

        db.session.commit()

        return jsonify({
            'message': 'Event updated successfully',
            'event': event.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print("UPDATE EVENT ERROR:", str(e))
        return jsonify({'error': str(e)}), 500


# ── DELETE EVENT ───────────────────────────────────
@events_bp.route('/<int:event_id>', methods=['DELETE'])
@jwt_required()
def delete_event(event_id):
    try:
        photographer_id = int(get_jwt_identity())

        event = Event.query.filter_by(
            id=event_id,
            photographer_id=photographer_id
        ).first_or_404()

        db.session.delete(event)
        db.session.commit()

        return jsonify({'message': 'Event deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        print("DELETE EVENT ERROR:", str(e))
        return jsonify({'error': str(e)}), 500


# ── SET EVENT COVER IMAGE ─────────────────────────
@events_bp.route('/<int:event_id>/set-cover', methods=['POST'])
@jwt_required()
def set_event_cover(event_id):
    try:
        photographer_id = int(get_jwt_identity())

        event = Event.query.filter_by(
            id=event_id,
            photographer_id=photographer_id
        ).first_or_404()

        data = request.get_json()
        if not data or 'photo_id' not in data:
            return jsonify({'error': 'photo_id is required'}), 400

        photo_id = data['photo_id']
        photo = Photo.query.filter_by(
            id=photo_id,
            event_id=event_id
        ).first_or_404()

        # Update event cover image to the photo filename
        event.cover_image = photo.filename
        db.session.commit()

        return jsonify({
            'message': 'Event cover image updated successfully',
            'event': event.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print("SET COVER ERROR:", str(e))
        return jsonify({'error': str(e)}), 500


# ── EVENT STATS ────────────────────────────────────
@events_bp.route('/<int:event_id>/stats', methods=['GET'])
@jwt_required()
def event_stats(event_id):
    try:
        photographer_id = int(get_jwt_identity())

        event = Event.query.filter_by(
            id=event_id,
            photographer_id=photographer_id
        ).first_or_404()

        total_photos = Photo.query.filter_by(event_id=event_id).count()
        processed = Photo.query.filter_by(event_id=event_id, is_processed=True).count()
        total_faces = db.session.query(
            db.func.sum(Photo.face_count)
        ).filter_by(event_id=event_id).scalar() or 0

        return jsonify({
            'event': event.to_dict(),
            'total_photos': total_photos,
            'processed': processed,
            'unprocessed': total_photos - processed,
            'total_faces': int(total_faces),
            'indexed': event.is_indexed,
            'progress': event.indexing_progress
        }), 200

    except Exception as e:
        print("EVENT STATS ERROR:", str(e))
        return jsonify({'error': 'Failed to fetch stats'}), 500


# ── DASHBOARD SUMMARY ──────────────────────────────
@events_bp.route('/dashboard/summary', methods=['GET'])
@jwt_required()
def dashboard_summary():
    try:
        photographer_id = int(get_jwt_identity())
        print(f"[DEBUG] DASHBOARD_SUMMARY: photographer_id={photographer_id}")

        events = Event.query.filter_by(
            photographer_id=photographer_id
        ).all()

        print(f"[DEBUG] DASHBOARD_SUMMARY: found {len(events)} events")
        total_events = len(events)
        event_ids = [e.id for e in events]

        total_photos = (
            Photo.query.filter(Photo.event_id.in_(event_ids)).count()
            if event_ids else 0
        )

        recent_events = sorted(
            events,
            key=lambda x: x.created_at,
            reverse=True
        )[:5]
        
        result = {
            'total_events': total_events,
            'total_photos': total_photos,
            'recent_events': [e.to_dict() for e in recent_events]
        }
        print(f"[DEBUG] DASHBOARD_SUMMARY: returning {result}")
        return jsonify(result), 200

    except Exception as e:
        print("DASHBOARD ERROR:", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to fetch dashboard data'}), 500