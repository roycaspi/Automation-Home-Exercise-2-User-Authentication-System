from datetime import timedelta

class Config:
    SQLALCHEMY_DATABASE_URI = 'postgresql://<db_username>:<db_password>@localhost:5432/<db_name>'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = '<your_jwt_secret_key>'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL  = False
    MAIL_USERNAME = 'your_email@gmail.com'
    MAIL_PASSWORD = 'your_email_password'
    MAIL_DEFAULT_SENDER = MAIL_USERNAME