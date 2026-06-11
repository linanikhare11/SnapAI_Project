# Lazy imports to prevent Flask startup hang on face_recognition library load
def register_routes(app):
    """Lazily register all route blueprints."""
    from .auth import auth_bp
    from .events import events_bp
    from .photos import photos_bp
    from .guest import guest_bp
    from .themes import themes_bp
    from .profile import profile_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(photos_bp)
    app.register_blueprint(guest_bp)
    app.register_blueprint(themes_bp)
    app.register_blueprint(profile_bp)

