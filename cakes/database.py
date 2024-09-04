from flask_sqlalchemy import SQLAlchemy

# Create a SQLAlchemy instance
db = SQLAlchemy()

def initialize_db(app):
    """
    Initialize the database with the Flask app.
    """
    db.init_app(app)
    app.app_context().push()
    db.create_all()