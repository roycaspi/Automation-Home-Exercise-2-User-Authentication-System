import os
import sys
import pytest
from flask_jwt_extended import decode_token

# Ensure project root is on sys.path so imports work
TEST_DIR = os.path.dirname(__file__)
PROJECT_DIR = os.path.abspath(os.path.join(TEST_DIR, ".."))
sys.path.insert(0, PROJECT_DIR)

from app import app as flask_app
from extensions import db
from models import User, PasswordResetToken

@pytest.fixture(scope="function")
def app():
    # Use in-memory SQLite & suppress email
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "testsecret",
        "MAIL_SUPPRESS_SEND": True,
        "WTF_CSRF_ENABLED": False,  # Disable CSRF for testing
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,  # Suppress warning
    })
    
    with flask_app.app_context():
        # Create all tables
        db.create_all()
        yield flask_app
        # Clean up after test
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope="function")
def client(app):
    return app.test_client()

@pytest.fixture(autouse=True)
def setup_app_context(app):
    """Ensure we're in app context for each test"""
    with app.app_context():
        yield

def test_register_invalid_password(client, app):
    with app.app_context():
        response = client.post("/register", json={
            "email": "user1@example.com",
            "password": "weakpass",
            "confirm": "weakpass"
        })
        assert response.status_code == 400
        data = response.get_json()
        assert "Password must be at least 8 characters" in data.get("error", "")

def test_register_success_creates_unverified_user(client, app):
    with app.app_context():
        response = client.post("/register", json={
            "email": "user2@example.com",
            "password": "StrongP@ss123",
            "confirm": "StrongP@ss123"
        })
        assert response.status_code == 201
        user = User.query.filter_by(email="user2@example.com").first()
        assert user is not None
        assert user.verified is False

def test_login_unverified_user_fails(client, app):
    with app.app_context():
        # Register user
        client.post("/register", json={
            "email": "user3@example.com",
            "password": "StrongP@ss123",
            "confirm": "StrongP@ss123"
        })
        
        # Try to login with unverified user
        response = client.post("/login", json={
            "email": "user3@example.com",
            "password": "StrongP@ss123"
        })
        assert response.status_code == 403
        data = response.get_json()
        assert "verify your email" in data.get("error", "").lower()

def test_verify_email_and_login_success(client, app):
    with app.app_context():
        # Register user
        client.post("/register", json={
            "email": "user4@example.com",
            "password": "StrongP@ss123",
            "confirm": "StrongP@ss123"
        })
        
        # Get user and verification token
        user = User.query.filter_by(email="user4@example.com").first()
        assert user is not None, "User should be created after registration"
        
        token_entry = PasswordResetToken.query.filter_by(user_id=user.id).first()
        assert token_entry is not None, "Verification token should be created"
        
        # Verify email
        verify_resp = client.get(f"/verify-email/{token_entry.token}")
        assert verify_resp.status_code == 200
        
        # Login should now succeed
        login_resp = client.post("/login", json={
            "email": "user4@example.com",
            "password": "StrongP@ss123"
        })
        assert login_resp.status_code == 200
        
        data = login_resp.get_json()
        assert "token" in data
        
        # Decode and verify JWT token
        decoded = decode_token(data["token"])
        assert str(decoded["sub"]) == str(user.id)

def test_dashboard_without_token_fails(client, app):
    with app.app_context():
        response = client.get("/dashboard")
        assert response.status_code in (401, 422)

def test_dashboard_with_valid_token(client, app):
    with app.app_context():
        # Register user
        client.post("/register", json={
            "email": "user5@example.com",
            "password": "StrongP@ss123",
            "confirm": "StrongP@ss123"
        })
        
        # Get user and verify email
        user = User.query.filter_by(email="user5@example.com").first()
        token_entry = PasswordResetToken.query.filter_by(user_id=user.id).first()
        client.get(f"/verify-email/{token_entry.token}")
        
        # Login to get JWT token
        login_resp = client.post("/login", json={
            "email": "user5@example.com",
            "password": "StrongP@ss123"
        })
        assert login_resp.status_code == 200
        
        jwt_token = login_resp.get_json()["token"]
        
        # Access dashboard with valid token
        dash_resp = client.get("/dashboard", headers={
            "Authorization": f"Bearer {jwt_token}"
        })
        assert dash_resp.status_code == 200
        
        data = dash_resp.get_json()
        assert data["email"] == "user5@example.com"
        assert "T" in data["created_at"]