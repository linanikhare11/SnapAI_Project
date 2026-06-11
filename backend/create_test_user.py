from models.database import db, Photographer
from config import Config
from flask import Flask
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    # Create a test photographer
    test_photo = Photographer(
        name='Test Photographer',
        email='test@example.com',
        password=generate_password_hash('password123')
    )
    db.session.add(test_photo)
    db.session.commit()
    print(f'✓ Created test photographer')
    print(f'  ID: {test_photo.id}')
    print(f'  Name: {test_photo.name}')
    print(f'  Email: {test_photo.email}')
