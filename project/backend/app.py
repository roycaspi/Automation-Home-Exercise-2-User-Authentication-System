from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import db, bcrypt, jwt, mail, limiter
from routes import auth_bp
from flask import send_from_directory

app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config.from_object(Config)

CORS(app)
db.init_app(app)
bcrypt.init_app(app)
jwt.init_app(app)
mail.init_app(app)
limiter.init_app(app)

app.register_blueprint(auth_bp)


@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
