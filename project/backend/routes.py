# backend/routes.py

import secrets
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, redirect, current_app
from flask_mail import Message
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from extensions import db, bcrypt, mail, limiter
from models import User, PasswordResetToken

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user (unverified). Sends an email verification link.
    Expected JSON body: { "email": "...", "password": "...", "confirm": "..." }
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    confirm = data.get('confirm')

    if not email or not password or password != confirm:
        return jsonify({'error': 'Invalid input'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'User already exists'}), 409

    # Create user with verified=False
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(email=email, password=hashed_password, verified=False)
    db.session.add(new_user)
    db.session.commit()  # Now new_user.id exists

    # Create email verification token (expires in 24 hours)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    verification_token = PasswordResetToken(
        user_id=new_user.id,
        token=token,
        expires_at=expires_at
    )
    db.session.add(verification_token)
    db.session.commit()

    # Send verification email
    verify_link = f"http://localhost:5000/verify-email/{token}"
    msg = Message(
        subject='Verify Your Email',
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[email]
    )
    msg.body = (
        "Thank you for registering!\n\n"
        "Please click the link below to verify your email and complete registration:\n\n"
        f"{verify_link}\n\n"
        "This link will expire in 24 hours."
    )
    mail.send(msg)

    return (
        jsonify({'message': 'Registration successful! Please check your inbox to verify your email before logging in.'}),
        201
    )


@auth_bp.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    """
    Verify a newly registered user's email. Consumes the token.
    """
    prt = PasswordResetToken.query.filter_by(token=token).first()
    if not prt or prt.expires_at < datetime.utcnow():
        return jsonify({'error': 'Invalid or expired token'}), 400

    user = User.query.get(prt.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.verified = True
    db.session.delete(prt)
    db.session.commit()

    return jsonify({'message': 'Email verified successfully. You may now log in.'})


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """
    Log in a verified user. Returns a JWT.
    Expected JSON body: { "email": "...", "password": "...", "remember": <bool> (optional) }
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    remember = data.get('remember', False)

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401

    if not user.verified:
        return jsonify({'error': 'Please verify your email before logging in.'}), 403

    if not bcrypt.check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    expires = timedelta(days=30) if remember else timedelta(hours=1)
    token = create_access_token(identity=str(user.id), expires_delta=expires)
    return jsonify({'token': token})


@auth_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    """
    Protected route: returns user info (email and created_at).
    """
    user_id_str = get_jwt_identity()
    user = User.query.get(int(user_id_str))
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'email': user.email,
        'created_at': user.created_at.isoformat()
    })


@auth_bp.route('/reset-password-request', methods=['POST'])
def reset_password_request():
    """
    Begin password reset: generate a token and email a reset link.
    Expected JSON body: { "email": "..." }
    """
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({'error': 'Email is required'}), 400

    user = User.query.filter_by(email=email).first()
    # Always respond with 200 to avoid revealing which emails exist
    if not user:
        return jsonify({'message': 'If that email is registered, a reset link has been sent.'})

    # Create password-reset token (expires in 1 hour)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    prt = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
    db.session.add(prt)
    db.session.commit()

    reset_link = f"http://localhost:5000/index.html?token={token}"
    msg = Message(
        subject='Reset Your Password',
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[email]
    )
    msg.body = f"Click here to reset your password: {reset_link}"
    mail.send(msg)

    return jsonify({'message': 'If that email is registered, a reset link has been sent.'})


@auth_bp.route('/reset-password/<token>', methods=['POST'])
def reset_password(token):
    """
    Complete password reset: consume the token and set a new password.
    Expected JSON body: { "password": "...", "confirm": "..." }
    """
    data = request.get_json()
    password = data.get('password')
    confirm = data.get('confirm')

    if not password or password != confirm:
        return jsonify({'error': 'Passwords must match and be valid.'}), 400

    prt = PasswordResetToken.query.filter_by(token=token).first()
    if not prt or prt.expires_at < datetime.utcnow():
        return jsonify({'error': 'Invalid or expired token'}), 400

    user = User.query.get(prt.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.password = bcrypt.generate_password_hash(password).decode('utf-8')
    db.session.delete(prt)
    db.session.commit()

    return jsonify({'message': 'Password reset successfully.'})


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def profile():
    """
    Edit profile: currently only supports password change.
    Expected JSON body: { "password": "..." }
    """
    user_id_str = get_jwt_identity()
    user = User.query.get(int(user_id_str))
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    new_password = data.get('password')
    if not new_password:
        return jsonify({'error': 'No update data provided'}), 400

    user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    db.session.commit()

    return jsonify({'message': 'Password updated successfully.'})
