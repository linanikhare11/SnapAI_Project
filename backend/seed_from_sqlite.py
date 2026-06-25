"""
seed_from_sqlite.py
-------------------
Copies ALL data from the local SQLite database (snapai.db) into the
Neon PostgreSQL database.  Run ONCE after the initial migration:

    python seed_from_sqlite.py

Safe to re-run: it skips rows that already exist (by primary key).
"""

import os
import sys
import sqlite3

# ── ensure imports resolve ──────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from flask import Flask
from config import Config
from models.database import db, Photographer, Event, Photo

SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'snapai.db')


def dict_from_row(row):
    return dict(zip(row.keys(), row))


def seed():
    # ── connect to SQLite ───────────────────────────────────────────────────
    if not os.path.exists(SQLITE_PATH):
        print(f"[ERROR] SQLite file not found: {SQLITE_PATH}")
        sys.exit(1)

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    cur = sqlite_conn.cursor()

    # ── boot Flask + Neon ───────────────────────────────────────────────────
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        neon_url = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"\n[INFO] Neon target: {neon_url[:60]}...")
        print(f"[INFO] SQLite source: {SQLITE_PATH}\n")

        # ── PHOTOGRAPHERS ───────────────────────────────────────────────────
        cur.execute("SELECT * FROM photographers")
        photographers = [dict_from_row(r) for r in cur.fetchall()]
        print(f"[INFO] Seeding {len(photographers)} photographer(s)...")
        seeded_p = 0
        for p in photographers:
            if Photographer.query.get(p['id']):
                print(f"  [SKIP] Photographer id={p['id']} already exists")
                continue
            obj = Photographer(
                id=p['id'],
                name=p['name'],
                email=p['email'],
                password=p['password'],
                logo_path=p.get('logo_path'),
                brand_color=p.get('brand_color', '#6C63FF'),
                watermark=p.get('watermark'),
                mobile_number=p.get('mobile_number'),
                specializations=p.get('specializations'),
                services=p.get('services'),
                technologies=p.get('technologies'),
                special_photos=p.get('special_photos'),
                profile_chat_messages=p.get('profile_chat_messages'),
                created_at=p.get('created_at'),
            )
            db.session.add(obj)
            seeded_p += 1
        db.session.commit()
        print(f"  => {seeded_p} new photographer(s) inserted.\n")

        # ── EVENTS ─────────────────────────────────────────────────────────
        cur.execute("SELECT * FROM events")
        events = [dict_from_row(r) for r in cur.fetchall()]
        print(f"[INFO] Seeding {len(events)} event(s)...")
        seeded_e = 0
        for e in events:
            if Event.query.get(e['id']):
                print(f"  [SKIP] Event id={e['id']} '{e['title']}' already exists")
                continue
            obj = Event(
                id=e['id'],
                photographer_id=e['photographer_id'],
                title=e['title'],
                description=e.get('description'),
                event_date=e.get('event_date'),
                slug=e['slug'],
                event_type=e.get('event_type', 'general'),
                cover_image=e.get('cover_image'),
                is_public=bool(e.get('is_public', 1)),
                access_pin=e.get('access_pin'),
                is_indexed=bool(e.get('is_indexed', 0)),
                indexing_progress=e.get('indexing_progress', 0),
                created_at=e.get('created_at'),
            )
            db.session.add(obj)
            seeded_e += 1
        db.session.commit()
        print(f"  => {seeded_e} new event(s) inserted.\n")

        # ── PHOTOS ─────────────────────────────────────────────────────────
        cur.execute("SELECT * FROM photos")
        photos = [dict_from_row(r) for r in cur.fetchall()]
        print(f"[INFO] Seeding {len(photos)} photo(s)...")
        seeded_ph = 0
        BATCH = 20
        for i, ph in enumerate(photos):
            if Photo.query.get(ph['id']):
                print(f"  [SKIP] Photo id={ph['id']} already exists")
                continue
            obj = Photo(
                id=ph['id'],
                event_id=ph['event_id'],
                filename=ph['filename'],
                original_name=ph['original_name'],
                thumbnail_path=ph.get('thumbnail_path'),
                file_size=ph.get('file_size'),
                face_encodings=ph.get('face_encodings'),
                face_count=ph.get('face_count', 0),
                is_processed=bool(ph.get('is_processed', 0)),
                uploaded_at=ph.get('uploaded_at'),
            )
            db.session.add(obj)
            seeded_ph += 1
            # commit in batches to avoid huge transactions
            if seeded_ph % BATCH == 0:
                db.session.commit()
                print(f"  ... committed batch ({seeded_ph}/{len(photos)})")
        db.session.commit()
        print(f"  => {seeded_ph} new photo(s) inserted.\n")

        # ── reset sequences so new inserts don't collide ────────────────────
        for table, col in [('photographers', 'id'), ('events', 'id'), ('photos', 'id')]:
            try:
                db.session.execute(
                    db.text(
                        f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), "
                        f"COALESCE(MAX({col}), 1)) FROM {table}"
                    )
                )
            except Exception as exc:
                print(f"  [WARN] Could not reset sequence for {table}: {exc}")
        db.session.commit()
        print("[INFO] PostgreSQL sequences reset to max existing IDs.\n")

    sqlite_conn.close()
    print("[DONE] All data seeded into Neon PostgreSQL successfully!\n")


if __name__ == '__main__':
    seed()
