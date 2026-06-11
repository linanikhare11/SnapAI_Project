#!/usr/bin/env python3
"""
migrate_to_cloudinary.py
------------------------
One-time migration script: uploads all existing local photos to Cloudinary
and updates the database with cloudinary_url + cloudinary_public_id.

Usage:
    python migrate_to_cloudinary.py
    python migrate_to_cloudinary.py --event-id 4      # migrate only event 4
    python migrate_to_cloudinary.py --dry-run          # preview without uploading
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# ── path setup ─────────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ── Flask + DB bootstrap ────────────────────────────────────────────────────────
logger.info("Bootstrapping Flask app...")
from flask import Flask
from models.database import db, Photo, ensure_schema
import cloudinary
import cloudinary.uploader
from io import BytesIO

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{BACKEND_DIR / "snapai.db"}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = str(BACKEND_DIR / 'uploads')
app.config['CLOUDINARY_CLOUD_NAME'] = os.environ.get('CLOUDINARY_CLOUD_NAME', 'dreczdguy')
app.config['CLOUDINARY_API_KEY']    = os.environ.get('CLOUDINARY_API_KEY',    '518614163582274')
app.config['CLOUDINARY_API_SECRET'] = os.environ.get('CLOUDINARY_API_SECRET', '6GrYqRlt_YuryP6dIo_BttdSy1M')

db.init_app(app)

from services.cloudinary_service import init_cloudinary, get_thumbnail_url
init_cloudinary(app)
logger.info("Cloudinary configured.")

# ── Migration logic ─────────────────────────────────────────────────────────────

def migrate_photos(event_id=None, dry_run=False):
    """Upload all local-only photos to Cloudinary and update DB records."""

    with app.app_context():
        # Query photos that have no Cloudinary data yet
        query = Photo.query.filter(Photo.cloudinary_public_id.is_(None))
        if event_id:
            query = query.filter(Photo.event_id == event_id)

        photos = query.order_by(Photo.event_id, Photo.id).all()

        if not photos:
            logger.info("✅ No photos need migration — all already on Cloudinary.")
            return

        logger.info(f"Found {len(photos)} photo(s) to migrate" +
                    (f" in event {event_id}" if event_id else "") +
                    (" (DRY RUN)" if dry_run else ""))

        success = 0
        skipped = 0
        failed  = 0

        for i, photo in enumerate(photos, 1):
            event_folder = os.path.join(
                app.config['UPLOAD_FOLDER'],
                f"event_{photo.event_id}",
                "originals",
                photo.filename
            )

            # Try common local paths
            local_paths = [
                event_folder,
                os.path.join(app.config['UPLOAD_FOLDER'],
                             f"event_{photo.event_id}", photo.filename),
            ]

            local_path = None
            for p in local_paths:
                if os.path.exists(p):
                    local_path = p
                    break

            if not local_path:
                logger.warning(f"[{i}/{len(photos)}] SKIP  photo id={photo.id} "
                               f"({photo.original_name}) — local file not found")
                skipped += 1
                continue

            # Determine Cloudinary public_id
            ext = photo.filename.rsplit('.', 1)[-1].lower() if '.' in photo.filename else 'jpg'
            base_name = photo.filename.rsplit('.', 1)[0]
            public_id = f"snapai/event_{photo.event_id}/originals/{base_name}"

            if dry_run:
                logger.info(f"[{i}/{len(photos)}] DRY   photo id={photo.id} "
                            f"({photo.original_name}) -> {public_id}")
                success += 1
                continue

            try:
                with open(local_path, 'rb') as f:
                    data = f.read()

                result = cloudinary.uploader.upload(
                    BytesIO(data),
                    public_id=public_id,
                    resource_type='image',
                    overwrite=False,        # don't re-upload if already exists
                    quality='auto',
                    fetch_format='auto',
                )

                # Build thumbnail URL via Cloudinary transformation
                thumbnail_url = get_thumbnail_url(result['public_id'], 500, 500)

                # Update DB
                photo.cloudinary_url      = result['secure_url']
                photo.cloudinary_public_id = result['public_id']
                photo.thumbnail_path      = thumbnail_url   # replace local path with CDN URL

                db.session.commit()

                logger.info(f"[{i}/{len(photos)}] ✓ OK   photo id={photo.id} "
                            f"({photo.original_name}) -> {result['public_id']}")
                success += 1

            except Exception as e:
                db.session.rollback()
                logger.error(f"[{i}/{len(photos)}] ✗ FAIL photo id={photo.id} "
                             f"({photo.original_name}): {e}")
                failed += 1

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Migration complete:")
        logger.info(f"  ✓  Uploaded : {success}")
        logger.info(f"  ⊘  Skipped  : {skipped}  (local file missing)")
        logger.info(f"  ✗  Failed   : {failed}")
        logger.info("=" * 60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrate local photos to Cloudinary')
    parser.add_argument('--event-id', type=int, default=None,
                        help='Migrate only photos belonging to this event ID')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview what would be migrated without actually uploading')
    args = parser.parse_args()

    migrate_photos(event_id=args.event_id, dry_run=args.dry_run)
