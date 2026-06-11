#!/usr/bin/env python3
"""
Complete database restoration from uploaded photos
"""
import os
import sys
from pathlib import Path
from datetime import datetime

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

os.environ.setdefault('FLASK_ENV', 'production')

from app import app
from models.database import db, Event, Photo, Photographer

def complete_restore():
    """Completely rebuild database with all photos"""
    
    uploads_dir = backend_dir / 'uploads'
    
    with app.app_context():
        print("\n" + "="*60)
        print("COMPLETE DATABASE RESTORATION")
        print("="*60)
        
        # Delete all existing data
        print("\n[1] Deleting existing data...")
        Photo.query.delete()
        Event.query.delete()
        Photographer.query.delete()
        db.session.commit()
        print("    ✓ All old data deleted")
        
        # Create photographer
        print("\n[2] Creating photographer...")
        photographer = Photographer(
            name='lina nikhare',
            email='lina@example.com',
            password='hashed_password',
            brand_color='#6C63FF'
        )
        db.session.add(photographer)
        db.session.commit()
        print(f"    ✓ Photographer created: ID={photographer.id}")
        
        # Scan and restore events
        print("\n[3] Scanning and restoring events...")
        event_count = 0
        photo_count = 0
        
        for event_folder in sorted(uploads_dir.iterdir()):
            if not event_folder.is_dir() or event_folder.name == 'themes':
                continue
            
            event_name = event_folder.name
            
            # Create event
            event = Event(
                photographer_id=photographer.id,
                title=event_name.replace('_', ' ').title(),
                description=f'Restored event',
                slug=event_name,
                event_type='general',
                is_public=True,
                is_indexed=False,
                created_at=datetime.utcnow()
            )
            db.session.add(event)
            db.session.flush()  # Get event.id without committing yet
            
            # Scan and add photos
            originals_dir = event_folder / 'originals'
            if originals_dir.exists():
                photo_files = sorted(originals_dir.glob('*.*'))
                
                for photo_file in photo_files:
                    photo = Photo(
                        event_id=event.id,
                        filename=photo_file.name,
                        original_name=photo_file.name,
                        thumbnail_path=f'uploads/{event_name}/thumbnails/{photo_file.name}',
                        file_size=photo_file.stat().st_size,
                        face_count=0,
                        is_processed=False,
                        uploaded_at=datetime.utcnow()
                    )
                    db.session.add(photo)
                    photo_count += 1
            
            db.session.commit()
            event_count += 1
            print(f"    ✓ Event: {event.title} ({len(photo_files)} photos) - ID={event.id}")
        
        print("\n" + "="*60)
        print(f"✅ RESTORATION COMPLETE!")
        print("="*60)
        print(f"  • Photographers: 1")
        print(f"  • Events: {event_count}")
        print(f"  • Photos: {photo_count}")
        print("="*60 + "\n")
        
        # Verify
        print("VERIFICATION:")
        p = Photographer.query.first()
        events = Event.query.all()
        photos = Photo.query.all()
        print(f"  Photographers in DB: {Photographer.query.count()}")
        print(f"  Events in DB: {len(events)}")
        print(f"  Photos in DB: {len(photos)}")
        
        for e in events:
            ep = Photo.query.filter_by(event_id=e.id).count()
            print(f"    - {e.title}: {ep} photos")

if __name__ == '__main__':
    complete_restore()
