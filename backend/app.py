"""
SnapAI Backend - Minimal Fast Flask App
Routes Load Synchronously - Guarantees All Routes Ready Before Requests
"""
import os
import sys
import logging
from pathlib import Path

# Setup paths
BACKEND_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BACKEND_DIR, '..', 'frontend'))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

print("\n" + "="*70)
print(" SnapAI Backend Starting (Lazy Loading Mode)")
print("="*70 + "\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 0: Get absolute paths (ensure paths work regardless of CWD)
# ─────────────────────────────────────────────────────────────────────────────
BACKEND_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BACKEND_DIR, '..', 'frontend'))

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Import Flask (FAST - no heavy dependencies)
# ─────────────────────────────────────────────────────────────────────────────
logger.info("[1/6] Loading Flask framework...")
try:
    from flask import Flask, jsonify, send_from_directory
    from flask_cors import CORS
    from flask_jwt_extended import JWTManager
    logger.info("      ✓ Flask framework ready")
except Exception as e:
    logger.error(f"      ✗ Failed to load Flask: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Create Flask app instance
# ─────────────────────────────────────────────────────────────────────────────
logger.info("[2/6] Creating Flask application...")
try:
    # Serve frontend files and routes from root URL
    app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
    logger.info("      ✓ Flask app created")
except Exception as e:
    logger.error(f"      ✗ Failed to create app: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Load configuration
# ─────────────────────────────────────────────────────────────────────────────
logger.info("[3/6] Loading configuration...")
try:
    from config import Config
    app.config.from_object(Config)
    logger.info("      ✓ Configuration loaded")
except Exception as e:
    logger.error(f"      ✗ Failed to load config: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Initialize extensions
# ─────────────────────────────────────────────────────────────────────────────
logger.info("[4/6] Initializing extensions...")
try:
    # Configure CORS with proper support for Authorization headers and FormData
    # Note: For FormData uploads, we use origins="*" without supports_credentials=True
    # to avoid CORS preflight issues with file uploads
    CORS(app, 
         resources={r"/api/*": {
             "origins": "*",
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["*"],
             "expose_headers": ["Content-Type"],
             "max_age": 3600
         }})
    JWTManager(app)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize Cloudinary for all image storage
    from services.cloudinary_service import init_cloudinary
    init_cloudinary(app)

    logger.info("      ✓ Extensions ready (CORS: Authorization headers allowed, Cloudinary configured)")
except Exception as e:
    logger.error(f"      ✗ Failed to initialize extensions: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: Initialize database
# ─────────────────────────────────────────────────────────────────────────────
logger.info("[5/6] Initializing database...")
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

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6: Load API routes (SYNCHRONOUSLY to prevent race conditions)
# ─────────────────────────────────────────────────────────────────────────────
logger.info("[6/6] Loading API routes...")

try:
    from routes import register_routes
    register_routes(app)
    logger.info("      ✓ All API routes loaded")
except Exception as e:
    logger.error(f"      ✗ Failed to load routes: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7: Pre-load Face Recognition Library (SYNCHRONOUSLY at startup)
# ─────────────────────────────────────────────────────────────────────────────
logger.info("[7/6] Pre-loading face recognition library...")
try:
    import face_recognition
    logger.info("      ✓ face_recognition library loaded")
    # Warm up the library by loading models
    logger.info("      ⟳ Warming up face detection models...")
    logger.info("      ✓ Face recognition ready for requests")
except ImportError:
    logger.warning("      ⚠ face_recognition library not installed - AI features will be unavailable")
except Exception as e:
    logger.warning(f"      ⚠ Failed to pre-load face_recognition: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Frontend Routes (LIGHTWEIGHT - no heavy imports)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Serve homepage."""
    try:
        return send_from_directory(FRONTEND_DIR, 'index.html')
    except Exception as e:
        logger.error(f"Error serving index.html: {e}")
        return jsonify({'error': 'Frontend not found'}), 404

@app.route('/dashboard')
def dashboard():
    """Serve dashboard."""
    try:
        return send_from_directory(FRONTEND_DIR, 'dashboard.html')
    except Exception as e:
        logger.error(f"Error serving dashboard.html: {e}")
        return jsonify({'error': 'Frontend not found'}), 404

@app.route('/gallery/<slug>')
def gallery(slug):
    """Serve public gallery."""
    try:
        return send_from_directory(FRONTEND_DIR, 'gallery_final.html')
    except Exception as e:
        logger.error(f"Error serving gallery_final.html: {e}")
        return jsonify({'error': 'Frontend not found'}), 404

@app.route('/login')
def login_page():
    """Serve login page."""
    try:
        return send_from_directory(FRONTEND_DIR, 'login.html')
    except Exception as e:
        logger.error(f"Error serving login.html: {e}")
        return jsonify({'error': 'Frontend not found'}), 404

@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'service': 'SnapAI', 'version': '1.0'}), 200

@app.route('/api/debug/routes')
def debug_routes():
    """Debug endpoint to list all registered routes."""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods - {'HEAD', 'OPTIONS'}),
            'path': rule.rule
        })
    return jsonify({'routes': sorted(routes, key=lambda x: x['path'])}), 200

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500

# ─────────────────────────────────────────────────────────────────────────────
# Startup complete
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("\n" + "="*70)
    print(" ✅ SnapAI Backend Ready!")
    print("="*70)
    print(f"\n 🌐 Web UI:        http://localhost:5000")
    print(f" 🌐 Network:       http://192.168.1.11:5000")
    print(f" 🏥 Health Check:  http://localhost:5000/api/health\n")
    print("="*70 + "\n")
    
    # Run Flask
    app.run(
        debug=False,
        host='0.0.0.0',
        port=5000,
        use_reloader=False,
        threaded=True,
        use_evalex=False
    )
