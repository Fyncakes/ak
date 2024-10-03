from cakes import fyncakes_app 
import pymongo
import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from functools import wraps

# Application Setup
UPLOAD_FOLDER = 'static/FynCakes'
app = fyncakes_app()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif'}
app.secret_key = "aroncakes"

# MongoDB Configuration
mongo_uri = "mongodb://localhost:27017/"
client = MongoClient(mongo_uri)
db = client.fyncakes
cakes_collection = db['cakes']

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Routes
@app.route('/')
def home():
    return render_template('HomePage.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # Check if the 'cake_image' field is in the form
        if 'cake_image' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['cake_image']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        # Check if file has an allowed extension
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Save the file
            try:
                file.save(file_path)
            except Exception as e:
                flash(f'File save error: {e}', 'danger')
                return redirect(request.url)

            # Get form data
            cake_name = request.form['cake_name']
            cake_price = request.form['cake_price']
            cake_description = request.form['cake_description']
            
            # Construct the image URL (use relative path for serving static files)
            image_url = url_for('static', filename=f'FynCakes/{filename}')

            # Save to MongoDB
            cake_data = {
                'name': cake_name,
                'price': cake_price,
                'description': cake_description,
                'image': image_url  # Save the URL that points to the static image
            }
            cakes_collection.insert_one(cake_data)

            # Redirect or reload the upload page with success message
            flash('Upload successful!', 'success')
            return render_template('uploadPage.html', message='Upload successful!')

    return render_template('uploadPage.html', message=None)

@app.route('/customer')
def customer():
    cakes = cakes_collection.find()
    return render_template('CustomerPage.html', cakes=cakes)

@app.route('/about')
def about_us():
    return render_template('AboutPage.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Hash the password
        hashed_password = generate_password_hash(password)
        
        # Check if the user already exists
        existing_user = db.users.find_one({'email': email})
        
        if existing_user is None:
            # Insert the new user into the database
            db.users.insert_one({
                'email': email,
                'password': hashed_password
            })
            flash('User registered successfully!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email already registered.', 'danger')
            return redirect(url_for('signup'))

    return render_template('SignUp.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Find the user in the database
        user = db.users.find_one({'email': email})

        # Check if user exists and the password is correct
        if user and check_password_hash(user['password'], password):
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password!', 'danger')

    return render_template('Login.html')

@app.route('/checkout')
def checkout():
    return render_template('CheckoutPage.html')

# Run the Application
if __name__ == '__main__':
    app.run(host='localhost', port=2000, debug=True)
