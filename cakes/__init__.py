# cakes/__init__.py

import os
import certifi 
from flask import Flask
from flask_login import LoginManager
from pymongo import MongoClient

# Initialize LoginManager
login_manager = LoginManager()
login_manager.login_view = 'routes.login' # Tells LoginManager where to redirect non-logged-in users
login_manager.login_message_category = 'info' # Optional: for better flash messages

# Initialize MongoDB client
# We will use environment variables for this later, but for now, this is fine.
mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/fyncakes')
client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
db = client.fyncakes

def create_app():
    """
    Application factory function. Creates and configures the Flask app.
    """
    app = Flask(__name__)

    # --- Configuration ---
    # Load secret key from environment variable for security
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    
    # Configure upload folder and allowed extensions
    # Note: UPLOAD_FOLDER should be an absolute path for reliability
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'FynCakes')
    app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif'}
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB upload limit

    # --- Initialize Extensions ---
    login_manager.init_app(app)

    # --- User Loader for Flask-Login ---
    from .models import User  # Import here to avoid circular import issues
    
    @login_manager.user_loader
    def load_user(user_email):
        user_data = db.users.find_one({'email': user_email})
        if user_data:
            # We pass the entire user document to the User object now
            return User(user_data)
        return None

    # --- Register Blueprints ---
    # Blueprints organize our routes into distinct modules.
    from .routes import routes_bp
    app.register_blueprint(routes_bp)

    return app