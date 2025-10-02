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
        self.username = user_data.get('username', '')
        self.first_name = user_data.get('first_name', '')
        self.last_name = user_data.get('last_name', '')
        self.profile_image = user_data.get('profile_image', '')
        self.is_student = user_data.get('is_student', False)

    def get_id(self):
        """
        Required by Flask-Login. Returns a unique ID for the user.
        We use the email address as the unique ID.
        """
        return str(self.email)