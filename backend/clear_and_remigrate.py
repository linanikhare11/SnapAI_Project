"""
clear_and_remigrate.py
-----------------------
1. Drops all data from Neon PostgreSQL (photographers, events, photos)
2. Drops and recreates tables with the updated schema (adds cloudinary columns)
3. Resets all sequences to 1

Run from the backend directory:
    python clear_and_remigrate.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from flask import Flask
from config import Config
from models.database import db, ensure_schema


def clear_and_remigrate():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        url = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"\n[INFO] Connected to: {url[:60]}...")

        print("[INFO] Dropping all existing tables...")
        db.drop_all()
        print("[OK]   All tables dropped.")

        print("[INFO] Creating tables with updated schema...")
        db.create_all()
        print("[OK]   Tables created:")
        print("         - photographers  (with all profile columns)")
        print("         - events         (with indexing columns)")
        print("         - photos         (with cloudinary_url, cloudinary_public_id)")

        ensure_schema(app)
        print("[OK]   ensure_schema() ran -- all columns verified.")

    print("\n[DONE] Neon database is clean and ready for fresh data!\n")
    print("  Next steps:")
    print("  1. Register a new photographer account in the app")
    print("  2. Create a new event")
    print("  3. Upload photos -- they will be stored directly in Cloudinary\n")


if __name__ == '__main__':
    clear_and_remigrate()
