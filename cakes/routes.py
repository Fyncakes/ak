# cakes/routes.py

import os
import calendar
import io
from flask import (
    Blueprint, render_template, request, redirect, session, flash, url_for, 
    jsonify, current_app, Response
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import login_user, login_required, current_user, logout_user
from functools import wraps
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from . import db  # Import the db object from our __init__.py
from .models import User
from .forms import SignupForm, LoginForm # Import your new forms
from bson.objectid import ObjectId # Important: Import this to query by ID


# Create a Blueprint
routes_bp = Blueprint('routes', __name__)

# --- Helper Functions ---

def allowed_file(filename):
    """Checks if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def admin_required(f):
    """Decorator to restrict access to admin users."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Unauthorized access: This area is for admins only.', 'danger')
            return redirect(url_for('routes.login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Main Routes ---

@routes_bp.route('/')
def home():
    return render_template('HomePage.html')

@routes_bp.route('/customer')
@login_required
def customer():
    cakes = db.cakes.find()
    return render_template('CustomerPage.html', cakes=cakes)

@routes_bp.route('/about')
def about_us():
    return render_template('AboutPage.html')

@routes_bp.route('/checkout')
@login_required
def checkout():
    return render_template('CheckoutPage.html')

# --- Authentication Routes ---


@routes_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():  # This handles POST request, validation, and CSRF check
        hashed_password = generate_password_hash(form.password.data)
        db.users.insert_one({
            'email': form.email.data.lower(),
            'password': hashed_password,
            'role': 'customer'  # Securely set role to customer
        })
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('routes.login'))
    # For a GET request or if validation fails, it will render the template with the form object
    return render_template('SignUp.html', form=form)

@routes_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('routes.home'))

    form = LoginForm()
    if form.validate_on_submit():
        user_data = db.users.find_one({'email': form.email.data.lower()})

        if user_data and check_password_hash(user_data['password'], form.password.data):
            user_obj = User(user_data)
            login_user(user_obj)

            # Update last_login time
            db.customers.update_one(
                {'email': form.email.data.lower()},
                {'$set': {'last_login': datetime.now()}},
                upsert=True
            )

            flash('Login successful!', 'success')

            # Redirect to the page user was trying to access, or to a default page
            next_page = request.args.get('next')
            if user_obj.role == 'admin':
                return redirect(next_page or url_for('routes.admin_dashboard'))
            return redirect(next_page or url_for('routes.customer'))
        else:
            flash('Login Unsuccessful. Please check email and password.', 'danger')

    return render_template('Login.html', form=form)

@routes_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('routes.login'))

# --- Admin Routes ---

@routes_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload():
    if request.method == 'POST':
        if 'cake_image' not in request.files:
            flash('No file part', 'warning')
            return redirect(request.url)
        file = request.files['cake_image']
        if file.filename == '':
            flash('No selected file', 'warning')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            cake_data = {
                'name': request.form['cake_name'],
                'price': float(request.form['cake_price']),
                'description': request.form['cake_description'],
                'image': url_for('static', filename=f'FynCakes/{filename}')
            }
            db.cakes.insert_one(cake_data)
            flash(f"Cake '{cake_data['name']}' uploaded successfully!", 'success')
            return redirect(url_for('routes.upload'))

    return render_template('uploadPage.html')
    
@routes_bp.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    # Placeholder data until we implement the features
    total_sales = 0
    total_orders = db.orders.count_documents({})
    total_customers = db.customers.count_documents({})
    
    # Safely get sales data
    sales_pipeline = [
        {"$unwind": "$products"},
        {"$group": {"_id": None, "total_sales": {"$sum": "$products.price"}}}
    ]
    sales_data = list(db.orders.aggregate(sales_pipeline))
    if sales_data:
        total_sales = sales_data[0].get('total_sales', 0)

    # Note: 'clicks' are not implemented, so this will be empty for now.
    most_clicked_products = list(db.cakes.find(sort=[('clicks', -1)]).limit(5))
    deleted_orders = list(db.deleted_products.find())
    bought_products = list(db.purchased_products.find())
    customers = list(db.customers.find({}, {'email': 1, 'last_login': 1, 'role': 1}))

    return render_template('AdminDashboard.html',
                           total_sales=total_sales,
                           total_orders=total_orders,
                           total_customers=total_customers,
                           most_clicked_products=most_clicked_products,
                           deleted_orders=deleted_orders,
                           bought_products=bought_products,
                           customers=customers)

@routes_bp.route('/admin/sales-graph')
@login_required
@admin_required
def sales_graph():
    # This function remains largely the same but needs error handling
    try:
        pipeline = [
            {"$match": {"order_date": {"$exists": True, "$ne": None}}},
            {"$group": {
                "_id": {"year": {"$year": "$order_date"}, "month": {"$month": "$order_date"}},
                "total_sales": {"$sum": {"$sum": "$products.price"}}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1}}
        ]
        sales_data = list(db.orders.aggregate(pipeline))
        
        months = [f"{calendar.month_name[d['_id']['month']]} {d['_id']['year']}" for d in sales_data]
        sales = [d['total_sales'] for d in sales_data]

        fig, ax = plt.subplots()
        ax.plot(months, sales, marker='o', linestyle='-')
        ax.set(title='Monthly Sales Performance', xlabel='Month', ylabel='Sales (UGX)')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close(fig)
        
        return Response(buf.getvalue(), mimetype='image/png')
    except Exception as e:
        # Log the error and return a placeholder or error image
        print(f"Error generating sales graph: {e}")
        # You can create a simple "Error generating graph" image to return here
        return "Error generating graph", 500

# --- API-like Routes for Cart ---

@routes_bp.route('/confirm_purchase', methods=['POST'])
@login_required
def confirm_purchase():
    data = request.get_json()
    products = data.get('products', [])

    if not products:
        return jsonify({'success': False, 'message': 'Cart is empty.'}), 400

    db.purchased_products.insert_many(products)
    
    # We should also create a formal order document
    db.orders.insert_one({
        'customer_email': current_user.email,
        'products': products,
        'order_date': datetime.now(),
        'status': 'confirmed'
    })
    
    return jsonify({'success': True, 'message': 'Purchase confirmed!'})

@routes_bp.route('/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    data = request.get_json()
    product = data.get('product', {})
    
    if not product:
        return jsonify({'success': False, 'message': 'No product data received.'}), 400

    db.deleted_products.insert_one({
        'customer_email': current_user.email,
        'product_name': product.get('name'),
        'reason': 'User removed from cart',
        'deleted_at': datetime.now()
    })
    return jsonify({'success': True})
# (Add this code to the end of cakes/routes.py)

@routes_bp.route('/admin/edit_cake/<cake_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_cake(cake_id):
    """
    Route to edit an existing cake's details.
    """
    try:
        # Find the specific cake by its ID
        cake = db.cakes.find_one({'_id': ObjectId(cake_id)})
    except Exception:
        # This handles cases where the cake_id is not a valid ObjectId format
        flash('Invalid cake ID format.', 'danger')
        return redirect(url_for('routes.admin_dashboard'))

    if not cake:
        flash('Cake not found!', 'danger')
        return redirect(url_for('routes.admin_dashboard'))

    if request.method == 'POST':
        # Update the cake data with form values
        updated_data = {
            'name': request.form.get('cake_name'),
            'price': float(request.form.get('cake_price')),
            'description': request.form.get('cake_description')
        }
        db.cakes.update_one({'_id': ObjectId(cake_id)}, {'$set': updated_data})
        flash(f"'{updated_data['name']}' has been updated successfully!", 'success')
        return redirect(url_for('routes.manage_cakes'))

    # For a GET request, show the edit form with the cake's current data
    return render_template('edit_cake.html', cake=cake)


@routes_bp.route('/admin/delete_cake/<cake_id>', methods=['POST'])
@login_required
@admin_required
def delete_cake(cake_id):
    """
    Route to delete a cake from the database.
    """
    try:
        result = db.cakes.delete_one({'_id': ObjectId(cake_id)})
        if result.deleted_count == 1:
            flash('Cake deleted successfully!', 'success')
        else:
            flash('Error: Cake not found or could not be deleted.', 'danger')
    except Exception:
        flash('Invalid cake ID format.', 'danger')

    return redirect(url_for('routes.manage_cakes'))


@routes_bp.route('/admin/manage_cakes')
@login_required
@admin_required
def manage_cakes():
    """
    A new page to display all cakes in a table for management.
    """
    all_cakes = list(db.cakes.find())
    return render_template('manage_cakes.html', cakes=all_cakes)
# (Add this new route to your routes.py file)
@routes_bp.route('/place_order', methods=['POST'])
@login_required
def place_order():
    data = request.get_json()

    # Extract all data from the frontend
    products = data.get('products')
    total_amount = data.get('totalAmount')
    delivery_date_str = data.get('deliveryDate')
    phone_number = data.get('phoneNumber')
    payment_option = data.get('paymentOption')

    # Basic server-side validation
    if not all([products, total_amount, delivery_date_str, phone_number, payment_option]):
        return jsonify({'success': False, 'message': 'Missing order information.'}), 400

    # Calculate payment details
    amount_to_pay_now = total_amount
    payment_status = 'paid'
    if payment_option == 'deposit':
        amount_to_pay_now = total_amount * 0.8
        payment_status = 'pending_balance'

    # --- PAYMENT GATEWAY SIMULATION ---
    # In a real application, this is where you would make an API call to a service
    # like Africa's Talking to trigger the mobile money STK push to the user's phone.
    # The payment gateway would then give you a response (success or failure).
    # For now, we will assume it is always successful.
    
    # Create the final order document to save in the database
    order_document = {
        'customer_email': current_user.email,
        'products': products,
        'total_amount': total_amount,
        'amount_paid': amount_to_pay_now,
        'balance_due': total_amount - amount_to_pay_now,
        'payment_status': payment_status,
        'order_status': 'confirmed',
        'delivery_date': datetime.strptime(delivery_date_str, '%Y-%m-%d'),
        'customer_phone': phone_number,
        'order_placed_at': datetime.now()
    }

    db.orders.insert_one(order_document)

    # --- SMS NOTIFICATION SIMULATION ---
    # In a real application, you would now use an SMS API (like Africa's Talking or Twilio)
    # to send a confirmation message to the customer's phone number.
    # Example message: "Thank you for your FynCakes order! We've received your deposit of UGX {amount}.
    # Your cake will be ready on {delivery_date}. We will remind you to clear the balance."
    print(f"SIMULATING SMS to {phone_number}: Order confirmed!")

    return jsonify({
        'success': True,
        'message': 'Order placed successfully! We have sent a confirmation to your phone.'
    })
# (Add this new route to your routes.py file, for example, after the 'checkout' route)

@routes_bp.route('/cart')
@login_required
def cart():
    """Renders the shopping cart page."""
    return render_template('CartPage.html')

@routes_bp.route('/cart/items', methods=['GET'])
@login_required
def get_cart_items():
    """Fetches the cart items for the currently logged-in user from the database."""
    # Find all documents in the 'carts' collection that belong to this user
    cart_items = list(db.carts.find({'user_email': current_user.email}))
    
    # MongoDB's _id is a special object; we must convert it to a string to send it over the internet
    for item in cart_items:
        item['_id'] = str(item['_id'])
        
    return jsonify(cart_items)

@routes_bp.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart_db():
    """Adds a product to the user's cart in the database."""
    product_data = request.get_json()
    
    # Create a new document to insert into our 'carts' collection
    cart_item = {
        'user_email': current_user.email, # Link this item to the logged-in user
        'name': product_data.get('name'),
        'price': product_data.get('price'),
        'description': product_data.get('description'),
        'imageUrl': product_data.get('imageUrl')
    }
    
    db.carts.insert_one(cart_item)
    
    return jsonify({'success': True, 'message': 'Item added to cart.'})

@routes_bp.route('/cart/remove/<item_id>', methods=['POST'])
@login_required
def remove_from_cart_db(item_id):
    """Removes an item from the user's cart in the database using its unique ID."""
    # For security, we ensure we only delete an item if the _id matches AND it belongs to the current user
    result = db.carts.delete_one({'_id': ObjectId(item_id), 'user_email': current_user.email})
    
    if result.deleted_count == 1:
        return jsonify({'success': True, 'message': 'Item removed from cart.'})
    else:
        # This will happen if the item doesn't exist or the user tries to delete an item that isn't theirs
        return jsonify({'success': False, 'message': 'Item not found or unauthorized.'}), 404

# (Add this new route to the end of your routes.py file)

@routes_bp.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    """Deletes all cart items for the currently logged-in user from the database."""
    try:
        db.carts.delete_many({'user_email': current_user.email})
        return jsonify({'success': True, 'message': 'Cart cleared.'})
    except Exception as e:
        print(f"Error clearing cart: {e}")
        return jsonify({'success': False, 'message': 'Failed to clear cart.'}), 500





