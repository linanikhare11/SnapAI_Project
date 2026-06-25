import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file from the same directory as this config file
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


def _get_database_url():
    """
    Return the database URL, fixing the 'postgres://' prefix that some
    providers (e.g. Heroku, older Neon URLs) still emit.
    SQLAlchemy 1.4+ requires 'postgresql://'.
    """
    url = os.environ.get('DATABASE_URL', '')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url or f'sqlite:///{os.path.join(basedir, "snapai.db")}'


class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'snapai-super-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'True') == 'True'

    # Database — Neon PostgreSQL (falls back to local SQLite if DATABASE_URL is unset)
    SQLALCHEMY_DATABASE_URI = _get_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Extra engine options for Neon / psycopg2 (SSL is embedded in the URL,
    # but we keep pool settings sane for serverless connections)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {},  # SSL params already in the URL via ?sslmode=require
    }

    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # Upload (local fallback folder — kept for face-recognition temp usage)
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

    # Cloudinary (primary storage for all images)
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', 'dreczdguy')
    CLOUDINARY_API_KEY     = os.environ.get('CLOUDINARY_API_KEY',    '518614163582274')
    CLOUDINARY_API_SECRET  = os.environ.get('CLOUDINARY_API_SECRET', '6GrYqRlt_YuryP6dIo_BttdSy1M')

    # Face Recognition
    FACE_RECOGNITION_TOLERANCE = 0.38   # Higher tolerance for hog model (fast CPU-friendly)
    FACE_RECOGNITION_MODEL = 'hog'     # 'hog' (fast, CPU-friendly) or 'cnn' (slow, needs GPU)

    # Thumbnail
    THUMBNAIL_SIZE = (400, 400)
    WATERMARK_OPACITY = 0.4


