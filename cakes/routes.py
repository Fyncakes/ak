# --- Standard Library Imports ---
import os
import calendar
import io
import math
import random
from datetime import datetime, timedelta
from functools import wraps

# --- Third-party Library Imports ---
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from bson.objectid import ObjectId
from flask import (
    Blueprint, render_template, request, redirect, flash, url_for,
    jsonify, current_app, Response
)
from flask_login import login_user, login_required, current_user, logout_user
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer # Added for password reset

# --- Local Application Imports ---
from . import db, mail
from .models import User
# THIS IS THE CORRECTED LINE
from .forms import SignupForm, LoginForm, RequestResetForm, ResetPasswordForm


# --- Blueprint Configuration ---
routes_bp = Blueprint('routes', __name__)

# --- Centralized Constants for easy management ---
CAKES_PER_PAGE = 6
CATEGORIES = ["Ready Cake", "Orange Cake", "Vanilla Cake","Bread","Cookies","chocolate cakes", "Wedding Cake"]


# =============================================================================
# HELPER FUNCTIONS & DECORATORS
# =============================================================================

def allowed_file(filename):
    """Checks if an uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def admin_required(f):
    """Decorator to restrict access to admin users only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Unauthorized access: This area is for admins only.', 'danger')
            return redirect(url_for('routes.login'))
        return f(*args, **kwargs)
    return decorated_function

def _get_users_with_student_status(limit=None):
    """
    Fetches users with the 'customer' role and enriches them with an 'is_student' flag.
    - limit (int, optional): The maximum number of users to return.
    """
    pipeline = [
        {'$match': {'role': 'customer'}},
        {'$sort': {'_id': -1}}
    ]
    if limit:
        pipeline.append({'$limit': limit})
    
    pipeline.extend([
        {'$lookup': {
            'from': 'students', 'localField': 'email',
            'foreignField': 'user_email', 'as': 'student_info'
        }},
        {'$addFields': {'is_student': {'$gt': [{'$size': '$student_info'}, 0]}}}
    ])
    
    return list(db.users.aggregate(pipeline))


# =============================================================================
# PAGE RENDERING ROUTES (Public & User-facing)
# =============================================================================

@routes_bp.route('/')
def home():
    """Renders the homepage."""
    return render_template('HomePage.html')

@routes_bp.route('/about')
def about_us():
    """Renders the about us page."""
    return render_template('AboutPage.html')

@routes_bp.route('/customer')
def customer():
    """Renders the main product listing page with filtering, searching, and pagination."""
    selected_category = request.args.get('category')
    search_query = request.args.get('q', '').strip()
    
    query = {}
    if selected_category and selected_category in CATEGORIES:
        query['category'] = selected_category
    
    if search_query:
        query['name'] = {'$regex': f'^{search_query}', '$options': 'i'}

    total_cakes = db.cakes.count_documents(query)
    initial_cakes = list(db.cakes.find(query).limit(CAKES_PER_PAGE))
    total_pages = math.ceil(total_cakes / CAKES_PER_PAGE)
    
    return render_template('CustomerPage.html', 
                           cakes=initial_cakes, 
                           categories=CATEGORIES,
                           selected_category=selected_category,
                           search_query=search_query,
                           current_page=1, 
                           total_pages=total_pages)

@routes_bp.route('/cake/<cake_id>')
def cake_details(cake_id):
    """Renders the detailed page for a single cake."""
    try:
        cake = db.cakes.find_one({'_id': ObjectId(cake_id)})
        if not cake:
            flash('Sorry, that cake could not be found.', 'danger')
            return redirect(url_for('routes.customer'))
        
        related_cakes = list(db.cakes.find({
            'category': cake.get('category'), 
            '_id': {'$ne': ObjectId(cake_id)}
        }).limit(3))
        
        if len(related_cakes) < 3:
             more_cakes = list(db.cakes.find({'_id': {'$ne': ObjectId(cake_id)}}).limit(3 - len(related_cakes)))
             related_cakes.extend(more_cakes)

        return render_template('cake_details.html', cake=cake, related_cakes=related_cakes)
    except Exception:
        flash('Invalid cake ID provided.', 'danger')
        return redirect(url_for('routes.customer'))

@routes_bp.route('/tasting-events')
def tasting_events():
    """Renders the cake tasting events page."""
    today = datetime.now()
    year, month = today.year, today.month
    
    month_calendar = calendar.monthcalendar(year, month)
    saturdays = [week[calendar.SATURDAY] for week in month_calendar if week[calendar.SATURDAY] != 0]

    upcoming_dates = []
    if len(saturdays) >= 2 and saturdays[1] >= today.day:
        upcoming_dates.append(datetime(year, month, saturdays[1]))
    if len(saturdays) >= 4 and saturdays[3] >= today.day:
        upcoming_dates.append(datetime(year, month, saturdays[3]))

    if not upcoming_dates:
        month += 1
        if month > 12:
            month, year = 1, year + 1
        month_calendar = calendar.monthcalendar(year, month)
        saturdays = [week[calendar.SATURDAY] for week in month_calendar if week[calendar.SATURDAY] != 0]
        if len(saturdays) >= 2: upcoming_dates.append(datetime(year, month, saturdays[1]))
        if len(saturdays) >= 4: upcoming_dates.append(datetime(year, month, saturdays[3]))
    
    slide_images = []
    slides_path = os.path.join(current_app.static_folder, 'cake_slides')

    if os.path.isdir(slides_path):
        for filename in os.listdir(slides_path):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                image_url = url_for('static', filename=f'cake_slides/{filename}')
                slide_images.append(image_url)

    return render_template('tasting_events.html', 
                           dates=upcoming_dates, 
                           slide_images=slide_images)

@routes_bp.route('/cart')
@login_required
def cart():
    """Renders the user's shopping cart page."""
    return render_template('CartPage.html')

@routes_bp.route('/checkout')
@login_required
def checkout():
    """Renders the final checkout and payment page."""
    return render_template('CheckoutPage.html')

@routes_bp.route('/learning-class')
def learning_class():
    """Renders the online class information page."""
    return render_template('learning_class.html')

@routes_bp.route('/terms-of-service')
def terms_of_service():
    """Renders the Terms of Service page."""
    return render_template('terms_of_service.html')

@routes_bp.route('/wedding-cakes')
def wedding_gallery():
    """Renders the wedding cake showcase page."""
    wedding_cakes = list(db.cakes.find({'category': 'Wedding Cake'}))
    return render_template('wedding_gallery.html', cakes=wedding_cakes)


# =============================================================================
# AUTHENTICATION ROUTES
# =============================================================================

@routes_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handles new user registration and initiates email verification."""
    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        if db.users.find_one({'email': email}) or db.unverified_users.find_one({'email': email}):
            flash('This email is already in use or pending verification.', 'info')
            return redirect(url_for('routes.login'))

        verification_code = str(random.randint(100000, 999999))
        hashed_password = generate_password_hash(form.password.data)

        db.unverified_users.update_one(
            {'email': email},
            {'$set': {
                'username': form.username.data,
                'first_name': form.first_name.data,
                'last_name': form.last_name.data,
                'password': hashed_password,
                'verification_code': verification_code,
                'expires_at': datetime.now() + timedelta(minutes=15)
            }},
            upsert=True
        )

        msg = Message('Your FynCakes Verification Code', recipients=[email])
        msg.body = f'Welcome to FynCakes! Your verification code is: {verification_code}'
        try:
            mail.send(msg)
            flash('A verification code has been sent to your email.', 'success')
            return redirect(url_for('routes.verify_email', email=email))
        except Exception as e:
            flash(f'An error occurred while sending the email: {e}', 'danger')
            
    return render_template('SignUp.html', form=form)

@routes_bp.route('/verify/<email>', methods=['GET', 'POST'])
def verify_email(email):
    """Handles email verification and finalizes user registration."""
    if request.method == 'POST':
        submitted_code = request.form.get('verification_code')
        user_data = db.unverified_users.find_one({'email': email})

        if not user_data or user_data['expires_at'] < datetime.now():
            flash('Your verification code is invalid or has expired. Please sign up again.', 'danger')
            return redirect(url_for('routes.signup'))

        if user_data['verification_code'] == submitted_code:
            db.users.insert_one({
                'email': user_data['email'],
                'username': user_data.get('username'),
                'first_name': user_data.get('first_name'),
                'last_name': user_data.get('last_name'),
                'password': user_data['password'],
                'role': 'customer'
            })
            db.unverified_users.delete_one({'email': email})
            flash('Email verified successfully! You can now log in.', 'success')
            return redirect(url_for('routes.login'))
        else:
            flash('Invalid verification code.', 'danger')

    return render_template('verify.html', email=email)

@routes_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        return redirect(url_for('routes.home'))

    form = LoginForm()
    if form.validate_on_submit():
        user_data = db.users.find_one({'email': form.email.data.lower()})
        if user_data and check_password_hash(user_data['password'], form.password.data):
            user_obj = User(user_data)
            login_user(user_obj)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            
            if user_obj.role == 'admin':
                return redirect(url_for('routes.admin_dashboard'))
            return redirect(next_page or url_for('routes.customer'))
        else:
            flash('Login failed. Please check your email and password.', 'danger')

    return render_template('Login.html', form=form)

@routes_bp.route('/logout')
@login_required
def logout():
    """Handles user logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('routes.login'))

def get_reset_token(user_email, expires_sec=1800):
    """Generates a secure, timed token."""
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(user_email, salt='password-reset-salt')

def verify_reset_token(token, expires_sec=1800):
    """Verifies the reset token and returns the user's email."""
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        user_email = s.loads(token, salt='password-reset-salt', max_age=expires_sec)
    except Exception:
        return None
    return user_email

@routes_bp.route('/reset_password', methods=['GET', 'POST'])
def request_reset():
    """Handles the request for a password reset link."""
    if current_user.is_authenticated:
        return redirect(url_for('routes.home'))
    
    form = RequestResetForm()
    if form.validate_on_submit():
        user_data = db.users.find_one({'email': form.email.data})
        if user_data:
            token = get_reset_token(user_data['email'])
            msg = Message('Password Reset Request for FynCakes', 
                          recipients=[user_data['email']])
            msg.body = f'''To reset your password, visit the following link:
{url_for('routes.reset_password', token=token, _external=True)}

If you did not make this request, simply ignore this email and no changes will be made.
This link will expire in 30 minutes.
'''
            mail.send(msg)
        
        flash('If an account with that email exists, a password reset link has been sent.', 'info')
        return redirect(url_for('routes.login'))
        
    return render_template('request_reset.html', form=form)

@routes_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handles the actual password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('routes.home'))
        
    user_email = verify_reset_token(token)
    if user_email is None:
        flash('That is an invalid or expired token. Please try again.', 'warning')
        return redirect(url_for('routes.request_reset'))
        
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        db.users.update_one({'email': user_email}, {'$set': {'password': hashed_password}})
        flash('Your password has been updated! You are now able to log in.', 'success')
        return redirect(url_for('routes.login'))
        
    return render_template('reset_password.html', form=form)


# =============================================================================
# ADMIN PANEL ROUTES
# =============================================================================

@routes_bp.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """Renders the main admin dashboard with site statistics."""
    total_orders = db.orders.count_documents({})
    total_customers = db.users.count_documents({'role': 'customer'})
    sales_data = list(db.orders.aggregate([
        {"$group": {"_id": None, "total_sales": {"$sum": "$total_amount"}}}
    ]))
    total_sales = sales_data[0]['total_sales'] if sales_data else 0

    customers = _get_users_with_student_status(limit=10)

    return render_template('AdminDashboard.html',
                           total_sales=total_sales,
                           total_orders=total_orders,
                           total_customers=total_customers,
                           customers=customers)

@routes_bp.route('/admin/manage_orders')
@login_required
@admin_required
def manage_orders():
    """Renders a page to view all customer orders."""
    all_orders = list(db.orders.find().sort('_id', -1))
    return render_template('manage_orders.html', orders=all_orders)

@routes_bp.route('/admin/manage_users')
@login_required
@admin_required
def manage_users():
    """Renders a page to view all registered users."""
    all_users = _get_users_with_student_status()
    return render_template('manage_users.html', users=all_users)

@routes_bp.route('/admin/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload():
    """Handles the uploading of new cake products by an admin."""
    if request.method == 'POST':
        if 'cake_image' not in request.files or request.files['cake_image'].filename == '':
            flash('No image file selected', 'warning')
            return redirect(request.url)
            
        file = request.files['cake_image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            
            cake_data = {
                'name': request.form['cake_name'],
                'price': float(request.form['cake_price']),
                'description': request.form['cake_description'],
                'category': request.form['cake_category'],
                'image': url_for('static', filename=f'cake_uploads/{filename}')
            }
            db.cakes.insert_one(cake_data)
            flash(f"Cake '{cake_data['name']}' uploaded successfully!", 'success')
            return redirect(url_for('routes.manage_cakes'))

    return render_template('uploadPage.html')

@routes_bp.route('/admin/manage_cakes')
@login_required
@admin_required
def manage_cakes():
    """Renders a page where admins can view, edit, and delete all cakes."""
    all_cakes = list(db.cakes.find().sort('name', 1))
    return render_template('manage_cakes.html', cakes=all_cakes)

@routes_bp.route('/admin/edit_cake/<cake_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_cake(cake_id):
    """Handles editing an existing cake."""
    try:
        cake = db.cakes.find_one({'_id': ObjectId(cake_id)})
        if not cake:
            flash('Error: Cake not found.', 'danger')
            return redirect(url_for('routes.manage_cakes'))
    except Exception:
        flash('Invalid cake ID format.', 'danger')
        return redirect(url_for('routes.manage_cakes'))

    if request.method == 'POST':
        updated_data = {
            'name': request.form.get('cake_name'),
            'description': request.form.get('cake_description'),
            'price': float(request.form.get('cake_price')),
            'category': request.form.get('cake_category')
        }
        
        if 'cake_image' in request.files:
            file = request.files['cake_image']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    updated_data['image'] = url_for('static', filename=f'cake_uploads/{filename}')
        
        db.cakes.update_one({'_id': ObjectId(cake_id)}, {'$set': updated_data})
        flash(f"'{updated_data['name']}' has been updated successfully!", 'success')
        return redirect(url_for('routes.manage_cakes'))
        
    return render_template('edit_cake.html', cake=cake)

@routes_bp.route('/admin/delete_cake/<cake_id>', methods=['POST'])
@login_required
@admin_required
def delete_cake(cake_id):
    """Handles deleting a cake."""
    db.cakes.delete_one({'_id': ObjectId(cake_id)})
    flash('Cake deleted successfully!', 'success')
    return redirect(url_for('routes.manage_cakes'))


# =============================================================================
# API ENDPOINTS (for JavaScript)
# =============================================================================

@routes_bp.route('/api/get_cakes')
def get_cakes_api():
    """API endpoint to fetch a 'page' of cakes, now with search."""
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    
    skip = (page - 1) * CAKES_PER_PAGE
    category = request.args.get('category')
    search_query = request.args.get('q', '').strip()
    
    query = {}
    if category and category in CATEGORIES:
        query['category'] = category
        
    if search_query:
        query['name'] = {'$regex': f'^{search_query}', '$options': 'i'}

    cakes_cursor = db.cakes.find(query).skip(skip).limit(CAKES_PER_PAGE)
    cakes_list = []
    for cake in cakes_cursor:
        cake['_id'] = str(cake['_id'])
        cake['url'] = url_for('routes.cake_details', cake_id=cake['_id'])
        cakes_list.append(cake)
        
    return jsonify(cakes_list)

@routes_bp.route('/cart/items', methods=['GET'])
@login_required
def get_cart_items():
    """API endpoint to fetch the current user's cart items."""
    items = list(db.carts.find({'user_email': current_user.email}))
    for item in items:
        item['_id'] = str(item['_id'])
    return jsonify(items)

@routes_bp.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart_db():
    """API endpoint to add an item to the user's cart."""
    product_data = request.get_json()
    cart_item = {
        'user_email': current_user.email,
        'name': product_data.get('name'),
        'price': product_data.get('price'),
        'description': product_data.get('description'),
        'imageUrl': product_data.get('imageUrl')
    }
    db.carts.insert_one(cart_item)
    return jsonify({'success': True})

@routes_bp.route('/cart/remove/<item_id>', methods=['POST'])
@login_required
def remove_from_cart_db(item_id):
    """API endpoint to remove an item from the user's cart."""
    db.cakes.delete_one({'_id': ObjectId(item_id), 'user_email': current_user.email})
    return jsonify({'success': True})

@routes_bp.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    """API endpoint to clear all items from the user's cart."""
    db.carts.delete_many({'user_email': current_user.email})
    return jsonify({'success': True})

@routes_bp.route('/place_order', methods=['POST'])
@login_required
def place_order():
    """Handles the final order placement and sends a confirmation email."""
    data = request.get_json()
    products = data.get('products')
    total_amount = data.get('totalAmount')
    delivery_date_str = data.get('deliveryDate')
    phone_number = data.get('phoneNumber')
    
    if not all([products, total_amount, delivery_date_str, phone_number]):
        return jsonify({'success': False, 'message': 'Missing order information.'}), 400

    order_id = f"FYN-{random.randint(1000, 9999)}"
    order_document = {
        'order_id': order_id,
        'customer_email': current_user.email,
        'products': products,
        'total_amount': total_amount,
        'payment_status': 'pending_payment',
        'order_status': 'awaiting_payment',
        'delivery_date': datetime.strptime(delivery_date_str, '%Y-%m-%d'),
        'customer_phone': phone_number,
        'order_placed_at': datetime.now()
    }
    db.orders.insert_one(order_document)

    try:
        product_list_html = "".join([f"<li>{p['name']} - ${p['price']:.2f}</li>" for p in products])
        msg = Message(f"FynCakes Order Confirmation - #{order_id}", recipients=[current_user.email])
        msg.html = f"""
        <div style="font-family: sans-serif;">
            <h1>Thank You for Your Order!</h1>
            <p>Your order #{order_id} has been received and is awaiting payment.</p>
            <h3>Order Summary</h3>
            <ul>{product_list_html}</ul>
            <p><strong>Total Amount: Shs{total_amount:.2f}</strong></p>
            <h3>Next Steps: Payment</h3>
            <p>Please send the total amount via Mobile Money to <strong>0772 123 456</strong> using your Order ID <strong>({order_id})</strong> as the reason.</p>
        </div>
        """
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Failed to send order confirmation email for {order_id}: {e}")

    return jsonify({'success': True, 'message': f"Order #{order_id} placed! Please check your email for payment instructions."})

@routes_bp.route('/register-class', methods=['POST'])
@login_required
def register_class():
    """Handles a student's registration for the online class."""
    data = request.get_json()
    student_name = data.get('name')
    student_phone = data.get('phone')

    if not all([student_name, student_phone]):
        return jsonify({'success': False, 'message': 'Missing registration information.'}), 400

    if db.students.find_one({'user_email': current_user.email}):
        return jsonify({'success': False, 'message': 'You are already registered for this class.'}), 409

    student_document = {
        'user_email': current_user.email,
        'student_name': student_name,
        'student_phone': student_phone,
        'registration_date': datetime.now(),
        'course_fee': 300000,
        'amount_paid': 0,
        'payment_status': 'pending_deposit',
        'has_access': False
    }
    db.students.insert_one(student_document)

    try:
        msg = Message("Welcome to FynCakes Baking Class!", recipients=[current_user.email])
        msg.html = f"""
        <div style="font-family: sans-serif;">
            <h1>Your Spot is Reserved, {student_name}!</h1>
            <p>To complete your registration, please send a 50% deposit of <strong>Shs150,000</strong> via Mobile Money to <strong>0758 449 390</strong>.</p>
        </div>
        """
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Failed to send class registration email for {current_user.email}: {e}")

    return jsonify({'success': True, 'message': 'Your spot is reserved! Please check your email for payment instructions.'})
    