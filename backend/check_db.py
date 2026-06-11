#!/usr/bin/env python3
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

os.environ.setdefault('FLASK_ENV', 'production')

from app import app
from models.database import db, Event, Photographer, Photo

with app.app_context():
    photographers = Photographer.query.all()
    print(f"=== PHOTOGRAPHERS ({len(photographers)}) ===")
    for p in photographers:
        print(f"  ID: {p.id}, Name: {p.name}, Email: {p.email}")
    
    print(f"\n=== EVENTS ({Event.query.count()}) ===")
    events = Event.query.all()
    for e in events:
        photos = Photo.query.filter_by(event_id=e.id).count()
        print(f"  {e.id}: {e.title} (slug={e.slug}, photos={photos})")
    
    print(f"\n=== ALL PHOTOS ({Photo.query.count()}) ===")
    photos = Photo.query.all()
    print(f"  Total photos in database: {len(photos)}")
    
    # Test API response
    print(f"\n=== TESTING API ===")
    print("GET /api/events/ - should return events for photographer_id=2")
