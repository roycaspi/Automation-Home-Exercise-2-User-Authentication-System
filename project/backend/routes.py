from datetime import datetime, timedelta
import secrets
from flask_mail import Message
from models import PasswordResetToken, User
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from flask import Blueprint, request, jsonify
from extensions import db, bcrypt, mail, limiter, jwt
import re

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    confirm = data.get('confirm')

    if not email or not password or password != confirm:
        return jsonify({'error': 'Invalid input'}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'User already exists'}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, password=hashed_password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    remember = data.get('remember', False)

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    expires = timedelta(days=30) if remember else timedelta(hours=1)
    token = create_access_token(identity=str(user.id), expires_delta=expires)
    return jsonify({'token': token})

@auth_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return jsonify({'email': user.email, 'created_at': user.created_at.isoformat()})

# Password Reset Feature
@auth_bp.route('/reset-password-request', methods=['POST'])
def reset_password_request():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({'error': 'Email is required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'If that email is registered, a reset link has been sent.'})

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    prt = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
    db.session.add(prt)
    db.session.commit()

    msg = Message('Reset Your Password', recipients=[email])
    reset_link = f"http://localhost:5000/reset-password/{token}"
    msg.body = f"Click here to reset your password: {reset_link}"
    mail.send(msg)

    return jsonify({'message': 'If that email is registered, a reset link has been sent.'})

@auth_bp.route('/reset-password/<token>', methods=['POST'])
def reset_password(token):
    data = request.get_json()
    password = data.get('password')
    confirm = data.get('confirm')

    if not password or password != confirm:
        return jsonify({'error': 'Passwords must match and be valid'}), 400

    prt = PasswordResetToken.query.filter_by(token=token).first()
    if not prt or prt.expires_at < datetime.utcnow():
        return jsonify({'error': 'Invalid or expired token'}), 400

    user = User.query.get(prt.user_id)
    user.password = bcrypt.generate_password_hash(password).decode('utf-8')
    db.session.delete(prt)
    db.session.commit()

    return jsonify({'message': 'Password reset successfully'})

# Email Verification 
@auth_bp.route('/send-verification', methods=['POST'])
@jwt_required()
def send_verification():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.verified:
        return jsonify({'message': 'User already verified'}), 200

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    prt = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
    db.session.add(prt)
    db.session.commit()

    msg = Message('Verify Your Email', recipients=[user.email])
    verify_link = f"http://localhost:5000/verify-email/{token}"
    msg.body = f"Click here to verify your email: {verify_link}"
    mail.send(msg)

    return jsonify({'message': 'Verification email sent'})

@auth_bp.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    prt = PasswordResetToken.query.filter_by(token=token).first()
    if not prt or prt.expires_at < datetime.utcnow():
        return jsonify({'error': 'Invalid or expired token'}), 400

    user = User.query.get(prt.user_id)
    user.verified = True
    db.session.delete(prt)
    db.session.commit()

    return jsonify({'message': 'Email verified successfully'})

# Profile Update 
@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    data = request.get_json()
    user = User.query.get(user_id)

    email = data.get('email')
    password = data.get('password')

    if email:
        user.email = email
    if password:
        user.password = bcrypt.generate_password_hash(password).decode('utf-8')

    db.session.commit()
    return jsonify({'message': 'Profile updated'})

# Remember Me Functionality
# @auth_bp.route('/login', methods=['POST'])
# def login():
#     data = request.get_json()
#     email = data.get('email')
#     password = data.get('password')
#     remember = data.get('remember', False)

#     user = User.query.filter_by(email=email).first()
#     if not user or not bcrypt.check_password_hash(user.password, password):
#         return jsonify({'error': 'Invalid credentials'}), 401

#     expires = timedelta(days=30) if remember else timedelta(hours=1)
#     token = create_access_token(identity=user.id, expires_delta=expires)
#     return jsonify({'token': token})

# # Rate Limiting
# @auth_bp.route('/login', methods=['POST'])
# @limiter.limit("5 per minute")
# def rate_limited_login():
#     return login()