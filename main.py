from cakes import fyncakes_app 
import pymongo
import hashlib
import os
import uuid
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, json, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from functools import wraps
from flask import send_from_directory
from werkzeug.utils import secure_filename

# Application Setup
UPLOAD_FOLDER = 'FynCakes'
app = fyncakes_app()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = "aroncakes"

# MongoDB Configuration
mongo_uri = "mongodb://localhost:27017/"
client = MongoClient(mongo_uri)
db = client.fyncakes

# Routes
@app.route('/')
def home():
    return render_template('HomePage.html')

@app.route('/customer')
def customer():
    return render_template('CustomerPage.html')

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
if __name__== '__main__':
    app.run(host='localhost', port=2000, debug=True)
