#!/usr/bin/env python3
"""
Restore events from existing photo folders in uploads/
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Setup path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

os.environ.setdefault('FLASK_ENV', 'production')

# Import app and models
from app import app
from models.database import db, Event, Photo, Photographer

def restore_events():
    """Scan uploads folder and recreate database entries for events"""
    
    uploads_dir = backend_dir / 'uploads'
    
    with app.app_context():
        # Get or create default photographer (lina nikhare)
        photographer = Photographer.query.first()
        if not photographer:
            photographer = Photographer(
                name='lina nikhare',
                email='lina@example.com',
                password='hashed_password_here',
                brand_color='#6C63FF'
            )
            db.session.add(photographer)
            db.session.commit()
            print(f"✓ Created photographer: {photographer.name}")
        else:
            print(f"✓ Using existing photographer: {photographer.name}")
        
        # Scan event folders
        for event_folder in sorted(uploads_dir.iterdir()):
            if not event_folder.is_dir() or event_folder.name == 'themes':
                continue
            
            event_name = event_folder.name
            
            # Check if event already exists
            existing_event = Event.query.filter_by(slug=event_name).first()
            if existing_event:
                print(f"⊙ Event '{event_name}' already exists, skipping...")
                continue
            
            # Create event
            event = Event(
                photographer_id=photographer.id,
                title=event_name.replace('_', ' ').title(),
                description=f'Restored event from {event_name}',
                slug=event_name,
                event_type='general',
                is_public=True,
                is_indexed=False,
                created_at=datetime.utcnow()
            )
            db.session.add(event)
            db.session.commit()
            print(f"✓ Restored event: {event.title} (ID: {event.id})")
            
            # Scan photos in this event
            originals_dir = event_folder / 'originals'
            if originals_dir.exists():
                photo_files = sorted(originals_dir.glob('*.*'))
                
                for photo_file in photo_files:
                    # Check if photo already exists
                    existing_photo = Photo.query.filter_by(
                        event_id=event.id,
                        filename=photo_file.name
                    ).first()
                    
                    if existing_photo:
                        print(f"  ⊙ Photo '{photo_file.name}' already exists")
                        continue
                    
                    # Create photo record
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
                    db.session.commit()
                    print(f"  ✓ Restored photo: {photo_file.name}")
        
        print("\n" + "="*60)
        print("✅ Events restoration complete!")
        print("="*60)
        
        # Show summary
        events = Event.query.filter_by(photographer_id=photographer.id).all()
        print(f"\nPhotographer '{photographer.name}' now has {len(events)} events:")
        for event in events:
            photo_count = Photo.query.filter_by(event_id=event.id).count()
            print(f"  • {event.title}: {photo_count} photos")

if __name__ == '__main__':
    restore_events()
