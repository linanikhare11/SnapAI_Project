"""
migrate_neon.py
---------------
One-shot migration script: connects to the Neon PostgreSQL database and
creates all tables defined in the SQLAlchemy models (photographers, events,
photos).  Run this once from the backend directory:

    python migrate_neon.py
"""

import os
import sys

# Make sure we can import from the backend package
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from flask import Flask
from config import Config
from models.database import db, ensure_schema


def run_migration():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"\n[INFO] Connecting to: {db_url[:60]}...")
        try:
            # Create tables that don't exist yet (idempotent)
            db.create_all()
            print("[OK] db.create_all() completed -- all tables are present.")

            # Apply any ALTER TABLE additions for existing tables
            ensure_schema(app)
            print("[OK] ensure_schema() completed -- all columns are present.")

        except Exception as exc:
            print(f"[ERROR] Migration failed: {exc}")
            sys.exit(1)

    print("\n[DONE] Migration to Neon PostgreSQL completed successfully!\n")


if __name__ == '__main__':
    run_migration()
