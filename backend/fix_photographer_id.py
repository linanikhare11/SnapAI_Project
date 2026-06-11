#!/usr/bin/env python3
"""
Fix: Reassign all restored events to correct photographer (ID=2)
"""
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

os.environ.setdefault('FLASK_ENV', 'production')

from app import app
from models.database import db, Event, Photographer

with app.app_context():
    print("\n" + "="*70)
    print("FIXING: REASSIGN EVENTS TO CORRECT PHOTOGRAPHER")
    print("="*70)
    
    # Get correct photographer (nikharelina11@gmail.com)
    correct_photographer = Photographer.query.filter_by(
        email='nikharelina11@gmail.com'
    ).first()
    
    if not correct_photographer:
        print("✗ ERROR: nikharelina11@gmail.com photographer not found!")
        sys.exit(1)
    
    print(f"\n✓ Correct photographer: {correct_photographer.name} (ID={correct_photographer.id})")
    
    # Update all events to belong to correct photographer
    print(f"\n[1] Updating events ownership...")
    updated = 0
    
    # Get the restored events (from IDs 1, 2, 3)
    restored_event_ids = [1, 2, 3]
    
    for event_id in restored_event_ids:
        event = Event.query.get(event_id)
        if event:
            old_photo_id = event.photographer_id
            event.photographer_id = correct_photographer.id
            db.session.add(event)
            updated += 1
            print(f"    ✓ {event.title}: photographer_id {old_photo_id} → {correct_photographer.id}")
    
    db.session.commit()
    
    print(f"\n[2] Verification:")
    events = Event.query.filter_by(photographer_id=correct_photographer.id).all()
    print(f"    Events for {correct_photographer.name}: {len(events)}")
    for e in events:
        from models.database import Photo
        photo_count = Photo.query.filter_by(event_id=e.id).count()
        print(f"      • {e.title}: {photo_count} photos")
    
    print("\n" + "="*70)
    print("✅ FIX COMPLETE!")
    print("="*70)
    print("\nNow refresh your dashboard - events should appear! 🎉\n")
