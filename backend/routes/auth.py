"""
Auth Routes — Photographer Registration & Login
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import db, Photographer

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    required = ['name', 'email', 'password']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    if Photographer.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409

    hashed_pw = generate_password_hash(data['password'])
    photographer = Photographer(
        name=data['name'],
        email=data['email'],
        password=hashed_pw,
        brand_color=data.get('brand_color', '#6C63FF'),
        watermark=data.get('watermark', data['name'])
    )
    db.session.add(photographer)
    db.session.commit()

    token = create_access_token(identity=str(photographer.id))
    return jsonify({
        'message': 'Registered successfully',
        'token': token,
        'photographer': photographer.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400

    photographer = Photographer.query.filter_by(email=data['email']).first()
    if not photographer or not check_password_hash(photographer.password, data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    token = create_access_token(identity=str(photographer.id))
    return jsonify({
        'token': token,
        'photographer': photographer.to_dict()
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    photographer_id = int(get_jwt_identity())
    photographer = Photographer.query.get_or_404(photographer_id)
    return jsonify(photographer.to_dict()), 200


@auth_bp.route('/update-profile', methods=['PUT'])
@jwt_required()
def update_profile():
    photographer_id = int(get_jwt_identity())
    photographer = Photographer.query.get_or_404(photographer_id)
    data = request.get_json()

    for field in ['name', 'brand_color', 'watermark']:
        if field in data:
            setattr(photographer, field, data[field])

    db.session.commit()
    return jsonify({'message': 'Profile updated', 'photographer': photographer.to_dict()}), 200
