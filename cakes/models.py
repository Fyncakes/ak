# cakes/models.py

from flask_login import UserMixin

class User(UserMixin):
    """
    User model for Flask-Login.
    It takes a user document from MongoDB as input.
    """
    def __init__(self, user_data):
        self.user_data = user_data
        self.email = user_data.get('email')
        self.password = user_data.get('password')
        self.role = user_data.get('role', 'customer')

    def get_id(self):
        """
        Required by Flask-Login. Returns a unique ID for the user.
        We use the email address as the unique ID.
        """
        return str(self.email)