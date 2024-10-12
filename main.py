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
from flask import send_from_directory
from werkzeug.utils import secure_filename
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
orders_collection = db['orders']  # Collection for orders
customers_collection = db['customers']  # Collection for customer data
logs_collection = db['logs']  # Collection for user logs
purchased_products_collection = db['purchased_products']
deleted_products_collection = db['deleted_products']

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect unauthorized users to login page

# User Model
class User(UserMixin):
    def __init__(self, email, password):
        self.email = email
        self.password = password

    def get_id(self):
        return str(self.email)

# Load user from session
@login_manager.user_loader
def load_user(user_email):
    user = db.users.find_one({'email': user_email})
    if user:
        return User(user['email'], user['password'])
    return None

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
            return redirect(request.url)
        
        file = request.files['cake_image']
        if file.filename == '':
            return redirect(request.url)

        # Check if file has an allowed extension
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Save the file
            file.save(file_path)

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

            # Redirect to another page or reload the upload page with success message
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
            login_user(User(user['email'], user['password']))
            flash('Login successful!', 'success')
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

# Route to confirm purchase
@app.route('/confirm_purchase', methods=['POST'])
def confirm_purchase():
    data = request.json
    products = data.get('products', [])
    
    # Insert bought products into the purchased_products collection
    for product in products:
        purchased_products_collection.insert_one({
            'name': product['name'],
            'price': product['price'],
            'description': product['description'],
            'imageUrl': product['imageUrl'],
            'purchase_date': datetime.now()
        })
    
    return jsonify({'success': True})

# Route to remove product from cart and save in deleted_products collection
@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    data = request.json
    product = data.get('product', {})
    
    # Insert deleted product into the deleted_products collection
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
    # Step 1: Aggregate the sales data by month, filtering out missing order_date
    pipeline = [
        {
            "$match": {
                "order_date": {"$exists": True, "$ne": None}  # Ensure order_date exists
            }
        },
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$order_date"},
                    "month": {"$month": "$order_date"}
                },
                "total_sales": {"$sum": {"$sum": "$products.price"}}
            }
        },
        {
            "$sort": {"_id.year": 1, "_id.month": 1}  # Sort by year and month
        }
    ]

    sales_data = list(orders_collection.aggregate(pipeline))

    # Step 2: Prepare data for plotting
    months = []
    sales = []
    
    for data in sales_data:
        if data['_id']:  # Check if _id is valid
            year = data['_id'].get('year')
            month = data['_id'].get('month')
            
            if year is not None and month is not None:
                total_sales = data['total_sales']

                month_name = f"{calendar.month_name[month]} {year}"
                months.append(month_name)
                sales.append(total_sales)

    # Step 3: Generate graph using Matplotlib
    fig, ax = plt.subplots()
    ax.plot(months, sales, marker='o', linestyle='-', color='#f39c12')
    ax.set_xlabel('Month')
    ax.set_ylabel('Sales ($)')
    ax.set_title('Monthly Sales Performance')
    ax.xaxis.set_major_locator(MaxNLocator(nbins=12))  # Ensure that months are readable
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    # Step 4: Save plot to a BytesIO buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)  # Close the plot to avoid memory leaks

    # Step 5: Return the graph as a response
    return Response(buf, mimetype='image/png')


# Admin dashboard route
@app.route('/admin/dashboard')
@login_required  # Ensure only admin users can access this page
def admin_dashboard():
    # Calculate total sales
    total_sales = 0
    total_orders = orders_collection.count_documents({})

    # Calculate total sales amount
    sales_data = orders_collection.aggregate([
        {"$unwind": "$products"},
        {"$group": {"_id": None, "total_sales": {"$sum": "$products.price"}}}
    ])
    total_sales = next(sales_data, {}).get('total_sales', 0)

    # Calculate total views and likes (implement as per your data structure)
    total_views = 0  # You may need to modify this based on how you track views
    total_likes = 0  # You may need to modify this based on how you track likes

    # Get customer information
    total_customers = customers_collection.count_documents({})

    # Get the most clicked product
    most_clicked_product = db.products.find_one(sort=[('clicks', -1)])

    # Get the most deleted product
    most_deleted_product = deleted_products_collection.find_one(sort=[('deleted_at', -1)])

    # Get bought products
    bought_products = list(purchased_products_collection.find())

    # Get most clicked products
    most_clicked_products = list(db.products.find(sort=[('clicks', -1)]).limit(5))

    # Get deleted orders
    deleted_orders = list(deleted_products_collection.find())

    # Get customer log details
    customers = list(customers_collection.find())

    return render_template('AdminDashboard.html',
                           total_sales=total_sales,
                           total_orders=total_orders,
                           total_views=total_views,
                           total_likes=total_likes,
                           total_customers=total_customers,
                           most_clicked_product=most_clicked_product,
                           most_deleted_product=most_deleted_product,
                           bought_products=bought_products,
                           most_clicked_products=most_clicked_products,
                           deleted_orders=deleted_orders,
                           customers=customers)

if __name__ == '__main__':
    app.run(debug=True)
