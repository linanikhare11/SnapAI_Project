#!/usr/bin/env python3
"""
SnapAI Lightweight Backend
Minimal Flask app for testing
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Setup path
backend_dir = Path(__file__).parent
frontend_dir = backend_dir.parent / 'frontend'
sys.path.insert(0, str(backend_dir))

# Load .env so DATABASE_URL (Neon) and other secrets are available
load_dotenv(backend_dir / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("Importing Flask...")
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager

logger.info("Creating Flask app...")
app = Flask(__name__, static_folder=str(frontend_dir), static_url_path='')

# Basic config
os.environ.setdefault('FLASK_ENV', 'production')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'snapai-secret-key')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')

# ── Database: prefer Neon (DATABASE_URL from .env), fall back to local SQLite ──
_db_url = os.environ.get('DATABASE_URL', f'sqlite:///{backend_dir}/snapai.db')
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}
app.config['UPLOAD_FOLDER'] = str(backend_dir / 'uploads')

logger.info(f"Database: {_db_url[:60]}...")

logger.info("Initializing extensions...")
# Configure CORS with proper support for Authorization headers and FormData
CORS(app, 
     resources={r"/api/*": {
         "origins": "*",
         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         "allow_headers": ["Content-Type", "Authorization"],
         "expose_headers": ["Content-Type"],
         "supports_credentials": True,
         "max_age": 3600
     }})
logger.info("CORS configured: Authorization headers allowed")
JWTManager(app)

logger.info("Creating upload directory...")
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Cloudinary configuration
app.config['CLOUDINARY_CLOUD_NAME'] = os.environ.get('CLOUDINARY_CLOUD_NAME', 'dreczdguy')
app.config['CLOUDINARY_API_KEY']    = os.environ.get('CLOUDINARY_API_KEY',    '518614163582274')
app.config['CLOUDINARY_API_SECRET'] = os.environ.get('CLOUDINARY_API_SECRET', '6GrYqRlt_YuryP6dIo_BttdSy1M')

try:
    from services.cloudinary_service import init_cloudinary
    init_cloudinary(app)
    logger.info("Cloudinary configured: cloud=dreczdguy")
except Exception as e:
    logger.warning(f"Cloudinary init warning: {e}")

logger.info("Registering routes...")
# HEALTH CHECK ROUTE
@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'service': 'SnapAI'}), 200

# FRONTEND ROUTES - Serve HTML files
@app.route('/')
def index():
    """Serve home page."""
    try:
        return send_from_directory(str(frontend_dir), 'index.html')
    except Exception as e:
        logger.error(f"Error serving index.html: {e}")
        return jsonify({'error': 'Frontend not found'}), 404

@app.route('/login')
def login():
    """Serve login page."""
    try:
        return send_from_directory(str(frontend_dir), 'login.html')
    except Exception as e:
        logger.error(f"Error serving login.html: {e}")
        return jsonify({'error': 'Frontend not found'}), 404

@app.route('/dashboard')
def dashboard():
    """Serve dashboard page."""
    try:
        return send_from_directory(str(frontend_dir), 'dashboard.html')
    except Exception as e:
        logger.error(f"Error serving dashboard.html: {e}")
        return jsonify({'error': 'Frontend not found'}), 404

@app.route('/gallery/<slug>')
def gallery(slug):
    """Serve gallery page."""
    try:
        return send_from_directory(str(frontend_dir), 'gallery_final.html')
    except Exception as e:
        logger.error(f"Error serving gallery_final.html: {e}")
        return jsonify({'error': 'Frontend not found'}), 404


logger.info("Initializing database...")
try:
    from models.database import db, ensure_schema
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        ensure_schema(app)
    logger.info("      ✓ Database ready")
except Exception as e:
    logger.error(f"      ✗ Failed to initialize database: {e}")
    sys.exit(1)

logger.info("Loading API routes (synchronously)...")
try:
    from routes import register_routes
    register_routes(app)
    logger.info("      ✓ API routes loaded")
except Exception as e:
    logger.error(f"      ✗ Failed to load routes: {e}")
    sys.exit(1)

logger.info("=" * 60)
logger.info("✅ SnapAI Backend Ready!")
logger.info("=" * 60)
logger.info("🚀 Running on http://0.0.0.0:5000")
logger.info("=" * 60)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False, threaded=True)
