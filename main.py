from cakes import fyncakes_app
import pymongo
import hashlib
import os
import uuid
import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend
import matplotlib.pyplot as plt
import io
import calendar
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, json, send_from_directory, Response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from functools import wraps
from datetime import datetime
from matplotlib.ticker import MaxNLocator

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
orders_collection = db['orders']
customers_collection = db['customers']
logs_collection = db['logs']
purchased_products_collection = db['purchased_products']
deleted_products_collection = db['deleted_products']

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin):
    def __init__(self, email, password, role='customer'):
        self.email = email
        self.password = password
        self.role = role

    def get_id(self):
        return str(self.email)

# Load user from session
@login_manager.user_loader
def load_user(user_email):
    user = db.users.find_one({'email': user_email})
    if user:
        return User(user['email'], user['password'], user.get('role', 'customer'))
    return None

# Routes
@app.route('/')
def home():
    return render_template('HomePage.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'cake_image' not in request.files:
            return redirect(request.url)
        file = request.files['cake_image']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            cake_name = request.form['cake_name']
            cake_price = request.form['cake_price']
            cake_description = request.form['cake_description']
            image_url = url_for('static', filename=f'FynCakes/{filename}')

            cake_data = {
                'name': cake_name,
                'price': cake_price,
                'description': cake_description,
                'image': image_url
            }
            cakes_collection.insert_one(cake_data)

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
        role = request.form.get('role')  # Get role from the signup form

        hashed_password = generate_password_hash(password)
        existing_user = db.users.find_one({'email': email})

        if existing_user is None:
            db.users.insert_one({
                'email': email,
                'password': hashed_password,
                'role': role  # Store the user role
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

        user = db.users.find_one({'email': email})

        if user and check_password_hash(user['password'], password):
            db.customers.update_one(
                {'email': email},
                {'$set': {'last_login': datetime.now()}},
                upsert=True
            )

            login_user(User(user['email'], user['password'], user.get('role', 'customer')))
            flash('Login successful!', 'success')

            if user.get('role') == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password!', 'danger')

    return render_template('Login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/checkout')
def checkout():
    return render_template('CheckoutPage.html')

@app.route('/confirm_purchase', methods=['POST'])
def confirm_purchase():
    data = request.json
    products = data.get('products', [])

    for product in products:
        purchased_products_collection.insert_one({
            'name': product['name'],
            'price': product['price'],
            'description': product['description'],
            'imageUrl': product['imageUrl'],
            'purchase_date': datetime.now()
        })

    return jsonify({'success': True})

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    data = request.json
    product = data.get('product', {})

    deleted_products_collection.insert_one({
        'name': product['name'],
        'price': product['price'],
        'description': product['description'],
        'imageUrl': product['imageUrl'],
        'delete_reason': 'User removed from cart',
        'deleted_at': datetime.now()
    })

    return jsonify({'success': True})

@app.route('/admin/sales-graph')
@login_required
def sales_graph():
    pipeline = [
        {"$match": {"order_date": {"$exists": True, "$ne": None}}},
        {"$group": {
            "_id": {"year": {"$year": "$order_date"}, "month": {"$month": "$order_date"}},
            "total_sales": {"$sum": {"$sum": "$products.price"}}
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}}
    ]

    sales_data = list(orders_collection.aggregate(pipeline))
    months = []
    sales = []

    for data in sales_data:
        if data['_id']:
            year = data['_id'].get('year')
            month = data['_id'].get('month')
            if year is not None and month is not None:
                total_sales = data['total_sales']
                month_name = f"{calendar.month_name[month]} {year}"
                months.append(month_name)
                sales.append(total_sales)

    fig, ax = plt.subplots()
    ax.plot(months, sales, marker='o', linestyle='-', color='#f39c12')
    ax.set_xlabel('Month')
    ax.set_ylabel('Sales ($)')
    ax.set_title('Monthly Sales Performance')
    ax.xaxis.set_major_locator(MaxNLocator(nbins=12))
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)

    return Response(buf, mimetype='image/png')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('home'))

    total_sales = 0
    total_orders = orders_collection.count_documents({})
    sales_data = orders_collection.aggregate([
        {"$unwind": "$products"},
        {"$group": {"_id": None, "total_sales": {"$sum": "$products.price"}}}
    ])
    total_sales = next(sales_data, {}).get('total_sales', 0)

    total_customers = customers_collection.count_documents({})
    most_clicked_product = db.products.find_one(sort=[('clicks', -1)])
    most_deleted_product = deleted_products_collection.find_one(sort=[('deleted_at', -1)])
    bought_products = list(purchased_products_collection.find())
    most_clicked_products = list(db.products.find(sort=[('clicks', -1)]).limit(5))
    deleted_orders = list(deleted_products_collection.find())

    customers = list(db.customers.find({}, {'email': 1, 'last_login': 1, 'role': 1}))  # Retrieve roles

    return render_template('AdminDashboard.html',
                           total_sales=total_sales,
                           total_orders=total_orders,
                           total_customers=total_customers,
                           most_clicked_product=most_clicked_product,
                           most_deleted_product=most_deleted_product,
                           bought_products=bought_products,
                           most_clicked_products=most_clicked_products,
                           deleted_orders=deleted_orders,
                           customers=customers)  # Pass customers to template

if __name__ == '__main__':
    app.run(host='localhost', port=2000, debug=True)
