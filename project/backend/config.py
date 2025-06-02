from datetime import timedelta

class Config:
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:1q2w3e4R@localhost:5432/drivenetsdb'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = 'supersecret'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL  = False
    MAIL_USERNAME = 'caspi27@gmail.com'
    MAIL_PASSWORD = 'glxcshpnxxxvkgsv'
    MAIL_DEFAULT_SENDER = MAIL_USERNAME