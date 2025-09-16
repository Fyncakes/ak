# cakes/__init__.py

import os
import certifi 
from flask import Flask
from flask_login import LoginManager
from pymongo import MongoClient
from flask_mail import Mail

# Initialize LoginManager
login_manager = LoginManager()
login_manager.login_view = 'routes.login'
login_manager.login_message_category = 'info'

# Initialize MongoDB client
mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/fyncakes')
client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
db = client.fyncakes
mail = Mail()

def create_app():
    """
    Application factory function. Creates and configures the Flask app.
    """
    app = Flask(__name__)

    # --- Configuration ---
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    
    # Configure upload folder and allowed extensions
    upload_path = os.path.join(app.root_path, 'static', 'cake_uploads')
    app.config['UPLOAD_FOLDER'] = upload_path
    os.makedirs(upload_path, exist_ok=True) # This creates the folder if it doesn't exist
    
    app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    # --- Email Server Configuration ---
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT'))
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

    # --- Initialize Extensions ---
    login_manager.init_app(app)
    mail.init_app(app)

    # --- User Loader for Flask-Login ---
    from .models import User
    
    @login_manager.user_loader
    def load_user(user_email):
        user_data = db.users.find_one({'email': user_email})
        if user_data:
            return User(user_data)
        return None

    # --- Register Blueprints ---
    from .routes import routes_bp
    app.register_blueprint(routes_bp)

    return app