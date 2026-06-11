#!/usr/bin/env python3
"""Debug script to find which import is causing the hang."""
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    logger.info("1. Importing Flask...")
    from flask import Flask, jsonify, send_from_directory
    logger.info("   ✓ Flask imported")
    
    logger.info("2. Importing flask_cors...")
    from flask_cors import CORS
    logger.info("   ✓ flask_cors imported")
    
    logger.info("3. Importing flask_jwt_extended...")
    from flask_jwt_extended import JWTManager
    logger.info("   ✓ flask_jwt_extended imported")
    
    logger.info("4. Importing config...")
    from config import Config
    logger.info("   ✓ config imported")
    
    logger.info("5. Importing models.database...")
    from models.database import db
    logger.info("   ✓ models.database imported")
    
    logger.info("6. Importing routes.auth...")
    from routes.auth import auth_bp
    logger.info("   ✓ routes.auth imported")
    
    logger.info("7. Importing routes.events...")
    from routes.events import events_bp
    logger.info("   ✓ routes.events imported")
    
    logger.info("8. Importing routes.photos...")
    from routes.photos import photos_bp
    logger.info("   ✓ routes.photos imported")
    
    logger.info("9. Importing routes.guest...")
    from routes.guest import guest_bp
    logger.info("   ✓ routes.guest imported")
    
    logger.info("\n✅ All imports successful!")
    
except Exception as e:
    logger.error(f"\n❌ Import failed with error:\n{e}", exc_info=True)
    sys.exit(1)
