#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
os.environ.setdefault('FLASK_ENV', 'production')

from app import app
from models.database import db, Photographer

with app.app_context():
    # Check if photographer exists
    p = Photographer.query.filter_by(email='nikhareline11@gmail.com').first()
    
    if p:
        print(f"✓ Photographer already exists: {p.name} (ID={p.id})")
    else:
        # Create with password 'password' (you can change this)
        photographer = Photographer(
            name='lina nikhare',
            email='nikhareline11@gmail.com',
            password=generate_password_hash('password'),
            brand_color='#6C63FF'
        )
        db.session.add(photographer)
        db.session.commit()
        print(f"✓ Created photographer: {photographer.name} (ID={photographer.id})")
        print(f"  Email: nikhareline11@gmail.com")
        print(f"  Password: password")
