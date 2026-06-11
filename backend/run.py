#!/usr/bin/env python3
"""
SnapAI Backend Startup Script
Minimal initialization before Flask starts
"""
import os
import sys
import logging

# Setup logging FIRST, before any imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

try:
    logger.info("=" * 60)
    logger.info("SnapAI Backend Starting...")
    logger.info("=" * 60)
    
    # Import Flask and dependencies (fast)
    logger.info("Loading Flask framework...")
    from flask import Flask
    from flask_cors import CORS
    from flask_jwt_extended import JWTManager
    logger.info("✓ Flask loaded")
    
    # Import config
    logger.info("Loading configuration...")
    from config import Config
    logger.info("✓ Config loaded")
    
    # Import database
    logger.info("Loading database...")
    from models.database import db
    logger.info("✓ Database loaded")
    
    # Create app
    logger.info("Creating Flask application...")
    app = Flask(__name__, static_folder='../frontend', static_url_path='')
    app.config.from_object(Config)
    logger.info("✓ App created")
    
    # Setup extensions
    logger.info("Initializing extensions...")
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    JWTManager(app)
    logger.info("✓ Extensions initialized")
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    logger.info(f"✓ Upload folder ready: {app.config['UPLOAD_FOLDER']}")
    
    # Register routes (lazy loaded in __init__.py)
    logger.info("Registering API routes...")
    from routes import register_routes
    register_routes(app)
    logger.info("✓ Routes registered")
    
    # Create DB tables
    logger.info("Initializing database tables...")
    with app.app_context():
        db.create_all()
    logger.info("✓ Database ready")
    
    # Add basic health check
    @app.route('/api/health')
    def health():
        return {'status': 'ok', 'service': 'SnapAI'}, 200
    
    # Frontend routes
    from flask import send_from_directory
    
    @app.route('/')
    def index():
        return send_from_directory('../frontend', 'index.html')
    
    @app.route('/dashboard')
    def dashboard():
        return send_from_directory('../frontend', 'dashboard.html')
    
    logger.info("=" * 60)
    logger.info("✅ Backend Ready!")
    logger.info("=" * 60)
    logger.info(f"🚀 Starting Flask on 0.0.0.0:5000")
    logger.info("Visit: http://localhost:5000")
    logger.info("=" * 60)
    
    # Start Flask
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
    
except Exception as e:
    logger.error(f"❌ Startup failed: {e}", exc_info=True)
    sys.exit(1)
