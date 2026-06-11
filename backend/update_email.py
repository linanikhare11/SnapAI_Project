#!/usr/bin/env python3
import os, sys
from pathlib import Path
from werkzeug.security import generate_password_hash

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
os.environ['FLASK_ENV'] = 'production'

from app import app
from models.database import db, Photographer

with app.app_context():
    p = Photographer.query.first()
    if p:
        p.email = 'nikhareline11@gmail.com'
        p.password = generate_password_hash('password')
        db.session.commit()
        print(f"✓ Updated: {p.name} -> {p.email}")
    else:
        print("No photographer found")
