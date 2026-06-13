from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from sqlalchemy import inspect, text

db = SQLAlchemy()

class Photographer(db.Model):
    __tablename__ = 'photographers'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), nullable=False)
    email       = db.Column(db.String(120), unique=True, nullable=False)
    password    = db.Column(db.String(256), nullable=False)
    logo_path   = db.Column(db.String(256), nullable=True)
    brand_color = db.Column(db.String(10), default='#6C63FF')
    watermark   = db.Column(db.String(120), nullable=True)
    
    # Contact Information
    mobile_number = db.Column(db.String(20), nullable=True)
    
    # About Photographer - Services & Specializations
    specializations = db.Column(db.Text, nullable=True)  # JSON array: ["Wedding", "Birthday", "Party"]
    services = db.Column(db.Text, nullable=True)         # Service description
    technologies = db.Column(db.Text, nullable=True)     # Technology description
    
    # Portfolio - Special Photos
    special_photos = db.Column(db.Text, nullable=True)   # JSON array of photo IDs for portfolio
    profile_chat_messages = db.Column(db.Text, nullable=True)  # JSON array of chat messages
    
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    events = db.relationship('Event', backref='photographer', lazy=True, cascade='all, delete-orphan')

    def get_specializations(self):
        """Deserialize specializations from JSON."""
        if not self.specializations:
            return []
        try:
            return json.loads(self.specializations)
        except:
            return []
    
    def set_specializations(self, specs):
        """Serialize specializations to JSON."""
        self.specializations = json.dumps(specs) if specs else None
    
    def get_special_photos(self):
        """Deserialize special photos from JSON."""
        if not self.special_photos:
            return []
        try:
            return json.loads(self.special_photos)
        except:
            return []
    
    def set_special_photos(self, photo_ids):
        """Serialize special photos to JSON."""
        self.special_photos = json.dumps(photo_ids) if photo_ids else None

    def get_profile_chat_messages(self):
        """Deserialize profile chat messages from JSON."""
        if not self.profile_chat_messages:
            return []
        try:
            data = json.loads(self.profile_chat_messages)
            return data if isinstance(data, list) else []
        except:
            return []

    def set_profile_chat_messages(self, messages):
        """Serialize profile chat messages to JSON."""
        self.profile_chat_messages = json.dumps(messages) if messages else None

    def to_dict(self):
        return {
            'id':          self.id,
            'name':        self.name,
            'email':       self.email,
            'mobile_number': self.mobile_number,
            'logo_path':   self.logo_path,
            'brand_color': self.brand_color,
            'watermark':   self.watermark,
            'specializations': self.get_specializations(),
            'services':    self.services,
            'technologies': self.technologies,
            'special_photos': self.get_special_photos(),
            'profile_chat_messages': self.get_profile_chat_messages(),
            'created_at':  self.created_at.isoformat()
        }


class Event(db.Model):
    __tablename__ = 'events'

    id             = db.Column(db.Integer, primary_key=True)
    photographer_id= db.Column(db.Integer, db.ForeignKey('photographers.id'), nullable=False)
    title          = db.Column(db.String(200), nullable=False)
    description    = db.Column(db.Text, nullable=True)
    event_date     = db.Column(db.Date, nullable=True)
    slug           = db.Column(db.String(200), unique=True, nullable=False)
    event_type     = db.Column(db.String(50), default='general')  # wedding, birthday, party, general
    cover_image    = db.Column(db.String(256), nullable=True)
    is_public      = db.Column(db.Boolean, default=True)
    access_pin     = db.Column(db.String(10), nullable=True)
    is_indexed     = db.Column(db.Boolean, default=False)
    indexing_progress = db.Column(db.Integer, default=0)  # 0-100%
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    photos = db.relationship('Photo', backref='event', lazy=True, cascade='all, delete-orphan')

    def photo_count(self):
        return Photo.query.filter_by(event_id=self.id).count()

    def to_dict(self):
        return {
            'id':                 self.id,
            'photographer_id':    self.photographer_id,
            'title':              self.title,
            'description':        self.description,
            'event_date':         self.event_date.isoformat() if self.event_date else None,
            'slug':               self.slug,
            'event_type':         self.event_type,
            'cover_image':        self.cover_image,
            'is_public':          self.is_public,
            'is_indexed':         self.is_indexed,
            'indexing_progress':  self.indexing_progress,
            'photo_count':        self.photo_count(),
            'created_at':         self.created_at.isoformat()
        }


class Photo(db.Model):
    __tablename__ = 'photos'

    id              = db.Column(db.Integer, primary_key=True)
    event_id        = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    filename        = db.Column(db.String(256), nullable=False)
    original_name   = db.Column(db.String(256), nullable=False)
    thumbnail_path  = db.Column(db.String(256), nullable=True)
    file_size       = db.Column(db.Integer, nullable=True)
    face_encodings  = db.Column(db.Text, nullable=True)   # JSON array of face encodings
    face_count      = db.Column(db.Integer, default=0)
    is_processed    = db.Column(db.Boolean, default=False)
    uploaded_at     = db.Column(db.DateTime, default=datetime.utcnow)

    def get_face_encodings(self):
        """
        Safely deserialize face encodings from JSON.
        Returns empty list if data is None or corrupted.
        """
        if not self.face_encodings:
            return []
        try:
            return json.loads(self.face_encodings)
        except json.JSONDecodeError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to deserialize face_encodings for photo {self.id}: {e}")
            return []

    def set_face_encodings(self, encodings):
        self.face_encodings = json.dumps([enc.tolist() for enc in encodings])

    def to_dict(self):
        return {
            'id':             self.id,
            'event_id':       self.event_id,
            'filename':       self.filename,
            'original_name':  self.original_name,
            'thumbnail_path': self.thumbnail_path,
            'file_size':      self.file_size,
            'face_count':     self.face_count,
            'is_processed':   self.is_processed,
            'uploaded_at':    self.uploaded_at.isoformat()
        }


def ensure_schema(app):
    """Bring an existing SQLite database up to date without dropping data."""
    with app.app_context():
        if db.engine.dialect.name != 'sqlite':
            return

        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        if 'photographers' not in tables:
            return

        existing_columns = {column['name'] for column in inspector.get_columns('photographers')}
        required_columns = {
            'mobile_number': 'VARCHAR(20)',
            'specializations': 'TEXT',
            'services': 'TEXT',
            'technologies': 'TEXT',
            'special_photos': 'TEXT',
            'profile_chat_messages': 'TEXT',
        }

        missing_columns = [
            (column_name, column_type)
            for column_name, column_type in required_columns.items()
            if column_name not in existing_columns
        ]

        if not missing_columns:
            return

        for column_name, column_type in missing_columns:
            db.session.execute(
                text(f'ALTER TABLE photographers ADD COLUMN {column_name} {column_type}')
            )

        db.session.commit()
