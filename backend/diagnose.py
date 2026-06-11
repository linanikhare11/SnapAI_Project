#!/usr/bin/env python3
"""
Diagnose why events are not showing in dashboard
"""
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

os.environ.setdefault('FLASK_ENV', 'production')

from app import app
from models.database import db, Event, Photo, Photographer

with app.app_context():
    print("\n" + "="*70)
    print("DATABASE DIAGNOSTIC")
    print("="*70)
    
    # 1. Check photographers
    print("\n[1] PHOTOGRAPHERS:")
    photographers = Photographer.query.all()
    for p in photographers:
        print(f"    ID: {p.id}, Name: {p.name}, Email: {p.email}")
    
    # 2. Check events
    print("\n[2] EVENTS:")
    events = Event.query.all()
    print(f"    Total: {len(events)}")
    for e in events:
        photos = Photo.query.filter_by(event_id=e.id).count()
        print(f"    • ID: {e.id}, Title: {e.title}, Slug: {e.slug}, Photos: {photos}")
        print(f"      Photographer_ID: {e.photographer_id}")
        print(f"      Event_type: {e.event_type}, is_public: {e.is_public}")
    
    # 3. Check photos
    print("\n[3] PHOTOS:")
    photos = Photo.query.all()
    print(f"    Total: {len(photos)}")
    
    # 4. Test event.to_dict() serialization
    print("\n[4] EVENT SERIALIZATION TEST:")
    for e in events[:1]:
        try:
            d = e.to_dict()
            print(f"    ✓ {e.title} serializes correctly")
            print(f"      Keys: {list(d.keys())}")
        except Exception as ex:
            print(f"    ✗ ERROR serializing {e.title}: {ex}")
    
    # 5. Test photo query
    print("\n[5] PHOTO QUERY TEST:")
    if events:
        first_event = events[0]
        event_photos = Photo.query.filter_by(event_id=first_event.id).all()
        print(f"    {first_event.title} has {len(event_photos)} photos")
    
    print("\n" + "="*70)
