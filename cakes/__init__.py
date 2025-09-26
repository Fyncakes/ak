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

# Initialize Database (MongoDB Atlas or Mock)
try:
    # Try to connect to MongoDB Atlas first
    mongo_uri = os.environ.get('MONGO_URI', 'mongodb+srv://fyncakes:FynCakes123@cluster0.68beb34.mongodb.net/fyncakes?retryWrites=true&w=majority')
    
    # Check if password placeholder exists
    if '<db_password>' in mongo_uri:
        print("⚠️  Please replace <db_password> in MONGO_URI with your actual MongoDB Atlas password")
        print("   Current URI:", mongo_uri)
        raise Exception("Password placeholder not replaced")
    
    client = MongoClient(mongo_uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    # Test connection
    client.admin.command('ping')
    db = client.fyncakes
    print("✅ Connected to MongoDB Atlas successfully!")
    print(f"   Database: {db.name}")
    print(f"   Collections: {db.list_collection_names()}")
except Exception as e:
    # Fall back to mock database
    print("⚠️  MongoDB Atlas not available, using mock database for development")
    print(f"   Error: {str(e)}")
    from .mock_db import init_mock_db
    db = init_mock_db()
mail = Mail()

def create_app():
    """
    Application factory function. Creates and configures the Flask app.
    """
    app = Flask(__name__)

    # --- Configuration ---
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Configure upload folder and allowed extensions
    upload_path = os.path.join(app.root_path, 'static', 'cake_uploads')
    app.config['UPLOAD_FOLDER'] = upload_path
    os.makedirs(upload_path, exist_ok=True) # This creates the folder if it doesn't exist
    
    app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    # --- Email Server Configuration ---
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', '')

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