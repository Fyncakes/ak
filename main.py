from cakes import fyncakes_app 
import pymongo
import hashlib
import os
import uuid
import pandas as pd
import urllib.parse
from pymongo import MongoClient
from flask import render_template, request, redirect, session, flash, url_for,jsonify,Flask, json
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from bson import json_util
from flask_login import LoginManager, UserMixin, login_user,login_required, current_user, logout_user
from bson import ObjectId
from functools import wraps
from flask import send_from_directory
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'FynCakes'
app = fyncakes_app()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = "aroncakes"

@app.route('/')
def home():
    return render_template('HomePage.html')

@app.route('/customer')
def customer():
    return render_template('CustomerPage.html')

@app.route('/about')
def about_us():
    return render_template('AboutPage.html')

@app.route('/signup')
def signup():
    return render_template('SignUp.html')

@app.route('/checkout')
def checkout():
    return render_template('CheckoutPage.html')

if __name__== '__main__':
    app.run(host='localhost', port=2000, debug=True) 