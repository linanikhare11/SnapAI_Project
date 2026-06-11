import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'snapai-super-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'True') == 'True'

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(basedir, "snapai.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

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

