# In database.py

from flask_pymongo import PyMongo

# Create a PyMongo instance
mongo = PyMongo()

def initialize_db(app):
    """
    Initialize the database with the Flask app.
    """
    mongo.init_app(app)