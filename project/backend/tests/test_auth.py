
import unittest
import json
import secrets
from datetime import datetime, timedelta
from ..app import app
from ..extensions import db, bcrypt, jwt
from ..models import User, PasswordResetToken


class AuthTestCase(unittest.TestCase):
    def setUp(self):
        # Configure the Flask app for testing
        app.config['TESTING'] = True
        # Use an in-memory SQLite database for tests
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['JWT_SECRET_KEY'] = 'test-secret-key'
        app.config['WTF_CSRF_ENABLED'] = False

        # Create the test client and the in-memory database tables
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        # Drop all tables after each test
        with app.app_context():
            db.drop_all()

    def register_user(self, email, password, confirm):
        """Helper: POST /register"""
        return self.client.post(
            '/register',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'email': email, 'password': password, 'confirm': confirm})
        )

    def login_user(self, email, password, remember=False):
        """Helper: POST /login"""
        return self.client.post(
            '/login',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'email': email, 'password': password, 'remember': remember})
        )

    def test_registration_and_login(self):
        # 1a) Successful registration
        res = self.register_user('test@example.com', 'password123', 'password123')
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'User registered successfully')

        # 1b) Duplicate registration should return 409
        res_dup = self.register_user('test@example.com', 'password123', 'password123')
        self.assertEqual(res_dup.status_code, 409)

        # 1c) Successful login returns a token
        res_login = self.login_user('test@example.com', 'password123')
        self.assertEqual(res_login.status_code, 200)
        token = res_login.get_json().get('token')
        self.assertIsNotNone(token)

        # 1d) Wrong password returns 401
        res_wrong = self.login_user('test@example.com', 'wrongpass')
        self.assertEqual(res_wrong.status_code, 401)

    def test_dashboard_protection(self):
        # 2a) Access /dashboard without token → 422
        res = self.client.get('/dashboard')
        self.assertEqual(res.status_code, 422)

        # 2b) Register & login to get a valid token
        self.register_user('a@a.com', 'pass', 'pass')
        res_login = self.login_user('a@a.com', 'pass')
        token = res_login.get_json().get('token')

        # 2c) Access /dashboard WITH token → 200, returns email and created_at
        res_dash = self.client.get('/dashboard', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res_dash.status_code, 200)
        data = res_dash.get_json()
        self.assertEqual(data['email'], 'a@a.com')
        self.assertTrue('created_at' in data)

    def test_password_reset_flow(self):
        # 3a) Register the user
        self.register_user('reset@example.com', 'oldpass', 'oldpass')
        user = User.query.filter_by(email='reset@example.com').first()
        self.assertIsNotNone(user)

        # 3b) /reset-password-request should return 200
        res_req = self.client.post(
            '/reset-password-request',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'email': 'reset@example.com'})
        )
        self.assertEqual(res_req.status_code, 200)

        # 3c) There should be a token in PasswordResetToken table
        prt = PasswordResetToken.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(prt)

        # 3d) Wrong confirm password → 400
        res_bad = self.client.post(f'/reset-password/{prt.token}',
                                   headers={'Content-Type': 'application/json'},
                                   data=json.dumps({'password': 'new1', 'confirm': 'new2'}))
        self.assertEqual(res_bad.status_code, 400)

        # 3e) Valid reset → 200
        res_reset = self.client.post(f'/reset-password/{prt.token}',
                                     headers={'Content-Type': 'application/json'},
                                     data=json.dumps({'password': 'newpassword', 'confirm': 'newpassword'}))
        self.assertEqual(res_reset.status_code, 200)
        data_reset = res_reset.get_json()
        self.assertIn('message', data_reset)
        self.assertEqual(data_reset['message'], 'Password reset successfully')

        # 3f) The token row should be deleted
        prt_deleted = PasswordResetToken.query.filter_by(user_id=user.id).first()
        self.assertIsNone(prt_deleted)

        # 3g) Login with the new password
        res_login = self.login_user('reset@example.com', 'newpassword')
        self.assertEqual(res_login.status_code, 200)

    def test_email_verification_flow(self):
        # 4a) Register & login to get JWT
        self.register_user('verify@example.com', 'pass1', 'pass1')
        res_login = self.login_user('verify@example.com', 'pass1')
        token = res_login.get_json().get('token')

        # 4b) POST /send-verification → 200
        res_send = self.client.post('/send-verification', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res_send.status_code, 200)
        data_send = res_send.get_json()
        self.assertEqual(data_send['message'], 'Verification email sent')

        # 4c) There should be a token saved in PasswordResetToken
        user = User.query.filter_by(email='verify@example.com').first()
        prt = PasswordResetToken.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(prt)

        # 4d) GET /verify-email/<token> → 200 and user.verified = True
        res_verify = self.client.get(f'/verify-email/{prt.token}')
        self.assertEqual(res_verify.status_code, 200)
        data_verify = res_verify.get_json()
        self.assertEqual(data_verify['message'], 'Email verified successfully')

        updated_user = User.query.get(user.id)
        self.assertTrue(updated_user.verified)

        # 4e) Attempt to verify again with same or expired token → 400
        expired_token = secrets.token_urlsafe(32)
        expired_prt = PasswordResetToken(user_id=user.id, token=expired_token,
                                         expires_at=datetime.utcnow() - timedelta(minutes=1))
        db.session.add(expired_prt)
        db.session.commit()
        res_expired = self.client.get(f'/verify-email/{expired_token}')
        self.assertEqual(res_expired.status_code, 400)

    def test_profile_update(self):
        # 5a) Register & login
        self.register_user('profile@example.com', 'oldpass', 'oldpass')
        res_login = self.login_user('profile@example.com', 'oldpass')
        token = res_login.get_json().get('token')

        # 5b) PUT /profile (change email & password)
        res_update = self.client.put(
            '/profile',
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
            data=json.dumps({'email': 'newprofile@example.com', 'password': 'newpass'})
        )
        self.assertEqual(res_update.status_code, 200)
        data_update = res_update.get_json()
        self.assertEqual(data_update['message'], 'Profile updated')

        # 5c) Old credentials no longer work
        res_old_login = self.login_user('profile@example.com', 'oldpass')
        self.assertEqual(res_old_login.status_code, 401)

        # 5d) New credentials work
        res_new_login = self.login_user('newprofile@example.com', 'newpass')
        self.assertEqual(res_new_login.status_code, 200)

    def test_remember_me_token_expiry(self):
        # 6a) Register & login with remember=True
        self.register_user('remember@example.com', 'rmpass', 'rmpass')
        res_login = self.login_user('remember@example.com', 'rmpass', remember=True)
        self.assertEqual(res_login.status_code, 200)
        token_str = res_login.get_json().get('token')
        self.assertIsNotNone(token_str)

        # 6b) Decode the token to inspect exp vs. iat
        decoded = jwt.decode_token(token_str)
        exp_ts = decoded['exp']      # expiration (in seconds since epoch)
        iat_ts = decoded['iat']      # issued-at (in seconds)
        # Ensure the expiry is significantly further out (e.g. > 23 hours)
        self.assertTrue((exp_ts - iat_ts) > (23 * 3600))

    def test_rate_limiting_login(self):
        # 7a) Register
        self.register_user('rate@example.com', 'ratepass', 'ratepass')

        # 7b) Attempt 5 incorrect logins
        for _ in range(5):
            res = self.login_user('rate@example.com', 'wrongpass')
            # First few return 401, eventually we hit 429
            self.assertIn(res.status_code, (401, 429))

        # 7c) The 6th attempt in quick succession should be rate-limited (429)
        res_limit = self.login_user('rate@example.com', 'wrongpass')
        self.assertEqual(res_limit.status_code, 429)


if __name__ == '__main__':
    unittest.main()
