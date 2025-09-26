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
try:
    from bson.objectid import ObjectId
except ImportError:
    # Mock ObjectId for development without MongoDB
    class ObjectId:
        def __init__(self, oid=None):
            self.oid = oid or f"mock_{hash(str(oid)) % 10000}"
        
        def __str__(self):
            return self.oid
        
        def __eq__(self, other):
            return str(self) == str(other)
        
        @classmethod
        def is_valid(cls, oid):
            return True
from flask import (
    Blueprint, render_template, request, redirect, flash, url_for,
    jsonify, current_app, Response
)
from flask_login import login_user, login_required, current_user, logout_user
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer

# --- Local Application Imports ---
from . import db, mail
from .models import User
from .forms import SignupForm, LoginForm, RequestResetForm, ResetPasswordForm

# --- Blueprint Configuration ---
routes_bp = Blueprint('routes', __name__)

# --- Constants ---
CAKES_PER_PAGE = 6


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
    """Fetches users with the 'customer' role and enriches them with an 'is_student' flag."""
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
# PUBLIC-FACING ROUTES
# =============================================================================

@routes_bp.route('/')
def home():
    """Renders the homepage with dynamic content."""
    # Get featured cakes (latest 6 cakes)
    featured_cakes = list(db.cakes.find().sort('_id', -1).limit(6))
    
    # Get statistics for homepage
    total_cakes = db.cakes.count_documents({})
    total_customers = db.users.count_documents({'role': 'customer'})
    total_orders = db.orders.count_documents({})
    
    # Get recent testimonials (if any exist in the future)
    testimonials = [
        {
            'name': 'Sarah Johnson',
            'text': 'Absolutely delicious cakes! The attention to detail and the flavors are amazing. FynCakes is our go-to for every family celebration.',
            'rating': 5
        },
        {
            'name': 'Michael Davis', 
            'text': 'FynCakes made our wedding day extra special with the most beautiful and delicious cake. Thank you for the wonderful experience!',
            'rating': 5
        },
        {
            'name': 'Grace Mbabazi',
            'text': 'The best cakes in Kampala! Fresh, delicious, and beautifully decorated. My kids love them!',
            'rating': 5
        }
    ]
    
    return render_template('HomePage.html', 
                         featured_cakes=featured_cakes,
                         total_cakes=total_cakes,
                         total_customers=total_customers,
                         total_orders=total_orders,
                         testimonials=testimonials)

@routes_bp.route('/about')
def about_us():
    """Renders the about us page."""
    return render_template('AboutPage.html')

@routes_bp.route('/customer')
def customer():
    """Renders the main product listing page with dynamic filtering, searching, and pagination."""
    selected_category = request.args.get('category')
    search_query = request.args.get('q', '').strip()
    
    query = {}
    if selected_category:
        query['category'] = selected_category
    
    if search_query:
        query['name'] = {'$regex': search_query, '$options': 'i'}

    # Fetch dynamic categories from the database for the dropdown
    all_categories = db.cakes.distinct("category")
    all_categories.sort()

    total_cakes = db.cakes.count_documents(query)
    initial_cakes = list(db.cakes.find(query).limit(CAKES_PER_PAGE))
    total_pages = math.ceil(total_cakes / CAKES_PER_PAGE)
    
    return render_template('CustomerPage.html', 
                           cakes=initial_cakes,
                           categories=all_categories,
                           selected_category=selected_category,
                           search_query=search_query,
                           current_page=1, 
                           total_pages=total_pages)
                           
@routes_bp.route('/cake/<cake_id>')
def cake_details(cake_id):
    """Renders the detailed page for a single cake."""
    try:
        # Handle both ObjectId and string IDs for compatibility
        try:
            cake = db.cakes.find_one({'_id': ObjectId(cake_id)})
        except:
            cake = db.cakes.find_one({'_id': cake_id})
            
        if not cake:
            flash('Sorry, that cake could not be found.', 'danger')
            return redirect(url_for('routes.customer'))
        
        # Find related cakes from the same category
        try:
            related_cakes = list(db.cakes.find({
                'category': cake.get('category'), 
                '_id': {'$ne': ObjectId(cake_id)}
            }).limit(3))
        except:
            related_cakes = list(db.cakes.find({
                'category': cake.get('category'), 
                '_id': {'$ne': cake_id}
            }).limit(3))
        
        # If not enough related cakes, fill with other random cakes
        if len(related_cakes) < 3:
            try:
                more_cakes = list(db.cakes.find({'_id': {'$ne': ObjectId(cake_id)}}).limit(3 - len(related_cakes)))
            except:
                more_cakes = list(db.cakes.find({'_id': {'$ne': cake_id}}).limit(3 - len(related_cakes)))
            related_cakes.extend(more_cakes)

        return render_template('cake_details.html', cake=cake, related_cakes=related_cakes)
    except Exception:
        flash('Invalid cake ID provided.', 'danger')
        return redirect(url_for('routes.customer'))

@routes_bp.route('/tasting-events')
def tasting_events():
    """Renders the cake tasting events page."""
    # This logic seems complex and might be simplified, but is kept as is for now.
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
        if month > 12: month, year = 1, year + 1
        month_calendar = calendar.monthcalendar(year, month)
        saturdays = [week[calendar.SATURDAY] for week in month_calendar if week[calendar.SATURDAY] != 0]
        if len(saturdays) >= 2: upcoming_dates.append(datetime(year, month, saturdays[1]))
        if len(saturdays) >= 4: upcoming_dates.append(datetime(year, month, saturdays[3]))
    
    slide_images = []
    slides_path = os.path.join(current_app.static_folder, 'cake_slides')

    if os.path.isdir(slides_path):
        for filename in os.listdir(slides_path):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                slide_images.append(url_for('static', filename=f'cake_slides/{filename}'))

    return render_template('tasting_events.html', dates=upcoming_dates, slide_images=slide_images)

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
            flash('Your verification code is invalid or has expired. Pcake_categorylease sign up again.', 'danger')
            db.unverified_users.delete_one({'email': email}) # Clean up expired entry
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
            
            return redirect(url_for('routes.admin_dashboard')) if user_obj.role == 'admin' else redirect(next_page or url_for('routes.customer'))
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
        return s.loads(token, salt='password-reset-salt', max_age=expires_sec)
    except Exception:
        return None

@routes_bp.route('/reset_password', methods=['GET', 'POST'])
def request_reset():
    """Handles the request for a password reset link."""
    if current_user.is_authenticated: return redirect(url_for('routes.home'))
    
    form = RequestResetForm()
    if form.validate_on_submit():
        if db.users.find_one({'email': form.email.data}):
            token = get_reset_token(form.email.data)
            msg = Message('Password Reset Request for FynCakes', recipients=[form.email.data])
            msg.body = f'''To reset your password, visit the following link (expires in 30 mins):
{url_for('routes.reset_password', token=token, _external=True)}

If you did not make this request, simply ignore this email.
'''
            mail.send(msg)
        
        flash('If an account with that email exists, a password reset link has been sent.', 'info')
        return redirect(url_for('routes.login'))
        
    return render_template('request_reset.html', form=form)

@routes_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handles the actual password reset."""
    if current_user.is_authenticated: return redirect(url_for('routes.home'))
        
    user_email = verify_reset_token(token)
    if not user_email:
        flash('That is an invalid or expired token.', 'warning')
        return redirect(url_for('routes.request_reset'))
        
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        db.users.update_one({'email': user_email}, {'$set': {'password': hashed_password}})
        flash('Your password has been updated! You can now log in.', 'success')
        return redirect(url_for('routes.login'))
        
    return render_template('reset_password.html', form=form)


# =============================================================================
# ADMIN PANEL ROUTES
# =============================================================================

@routes_bp.route('/admin/dashboard')
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
@admin_required
def manage_orders():
    """Renders a page to view all customer orders."""
    all_orders = list(db.orders.find().sort('_id', -1))
    return render_template('manage_orders.html', orders=all_orders)

@routes_bp.route('/admin/manage_users')
@admin_required
def manage_users():
    """Renders a page to view all registered users."""
    all_users = _get_users_with_student_status()
    return render_template('manage_users.html', users=all_users)

@routes_bp.route('/admin/upload', methods=['GET', 'POST'])
@admin_required
def upload():
    """Handles uploading new cake products, providing categories for the form."""
    if request.method == 'POST':
        if 'cake_image' not in request.files or not request.files['cake_image'].filename:
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

    # Fetch categories for the GET request to populate the dropdown
    all_categories = db.cakes.distinct("category")
    all_categories.sort()
    return render_template('uploadPage.html', categories=all_categories)

@routes_bp.route('/admin/manage_cakes')
@admin_required
def manage_cakes():
    """Renders a page where admins can view, edit, and delete all cakes."""
    all_cakes = list(db.cakes.find().sort('name', 1))
    return render_template('manage_cakes.html', cakes=all_cakes)

@routes_bp.route('/admin/edit_cake/<cake_id>', methods=['GET', 'POST'])
@admin_required
def edit_cake(cake_id):
    """Handles editing an existing cake, providing categories for the form."""
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
        
        file = request.files.get('cake_image')
        if file and file.filename:
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                updated_data['image'] = url_for('static', filename=f'cake_uploads/{filename}')
        
        db.cakes.update_one({'_id': ObjectId(cake_id)}, {'$set': updated_data})
        flash(f"'{updated_data['name']}' has been updated successfully!", 'success')
        return redirect(url_for('routes.manage_cakes'))
        
    # Fetch categories for the GET request to populate the dropdown
    all_categories = db.cakes.distinct("category")
    all_categories.sort()
    return render_template('edit_cake.html', cake=cake, categories=all_categories)

@routes_bp.route('/admin/delete_cake/<cake_id>', methods=['POST'])
@admin_required
def delete_cake(cake_id):
    """Handles deleting a cake."""
    try:
        db.cakes.delete_one({'_id': ObjectId(cake_id)})
        flash('Cake deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting cake: {e}', 'danger')
    return redirect(url_for('routes.manage_cakes'))


# =============================================================================
# API ENDPOINTS (for JavaScript)
# =============================================================================

@routes_bp.route('/api/get_cakes')
def get_cakes_api():
    """API endpoint to fetch a 'page' of cakes with dynamic filtering."""
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    
    skip = (page - 1) * CAKES_PER_PAGE
    category = request.args.get('category')
    search_query = request.args.get('q', '').strip()
    
    query = {}
    if category: # Removed check against hardcoded list
        query['category'] = category
        
    if search_query:
        query['name'] = {'$regex': search_query, '$options': 'i'} # Use more flexible search

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
    for item in items: item['_id'] = str(item['_id'])
    return jsonify(items)

@routes_bp.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart_db():
    """API endpoint to add an item to the user's cart."""
    product_data = request.get_json()
    db.carts.insert_one({
        'user_email': current_user.email,
        'name': product_data.get('name'),
        'price': product_data.get('price'),
        'description': product_data.get('description'),
        'imageUrl': product_data.get('imageUrl')
    })
    return jsonify({'success': True})

@routes_bp.route('/cart/remove/<item_id>', methods=['POST'])
@login_required
def remove_from_cart_db(item_id):
    """API endpoint to remove an item from the user's cart."""
    # Note: This logic seems to use cake_id to delete from carts, might need review
    db.carts.delete_one({'_id': ObjectId(item_id), 'user_email': current_user.email})
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
    db.orders.insert_one({
        'order_id': order_id,
        'customer_email': current_user.email,
        'products': products,
        'total_amount': total_amount,
        'payment_status': 'pending_payment',
        'order_status': 'awaiting_payment',
        'delivery_date': datetime.strptime(delivery_date_str, '%Y-%m-%d'),
        'customer_phone': phone_number,
        'order_placed_at': datetime.now()
    })

    try:
        product_list_html = "".join([f"<li>{p['name']} - Shs {p['price']:,.0f}</li>" for p in products])
        msg = Message(f"FynCakes Order Confirmation - #{order_id}", recipients=[current_user.email])
        msg.html = f"""
        <div style="font-family: sans-serif;">
            <h1>Thank You for Your Order!</h1>
            <p>Your order #{order_id} has been received and is awaiting payment.</p>
            <h3>Order Summary</h3>
            <ul>{product_list_html}</ul>
            <p><strong>Total Amount: Shs {total_amount:,.0f}</strong></p>
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

    db.students.insert_one({
        'user_email': current_user.email,
        'student_name': student_name,
        'student_phone': student_phone,
        'registration_date': datetime.now(),
        'course_fee': 300000,
        'amount_paid': 0,
        'payment_status': 'pending_deposit',
        'has_access': False
    })

    try:
        msg = Message("Welcome to FynCakes Baking Class!", recipients=[current_user.email])
        msg.html = f"""
        <div style="font-family: sans-serif;">
            <h1>Your Spot is Reserved, {student_name}!</h1>
            <p>To complete your registration, please send a 50% deposit of <strong>Shs 150,000</strong> via Mobile Money to <strong>0758 449 390</strong>.</p>
        </div>
        """
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Failed to send class registration email for {current_user.email}: {e}")

    return jsonify({'success': True, 'message': 'Your spot is reserved! Please check your email for payment instructions.'})

@routes_bp.route('/api/update_cake/<cake_id>', methods=['PUT'])
@admin_required
def update_cake_api(cake_id):
    """API endpoint to update cake details."""
    try:
        data = request.get_json()
        
        # Update the cake in the database
        result = db.cakes.update_one(
            {'_id': cake_id},
            {'$set': data}
        )
        
        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Cake updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Cake not found or no changes made'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@routes_bp.route('/api/comments', methods=['GET'])
def get_comments():
    """Get all approved comments."""
    try:
        comments = list(db.comments.find({'approved': True}).sort('created_at', -1).limit(10))
        # Convert ObjectId to string for JSON serialization
        for comment in comments:
            comment['_id'] = str(comment['_id'])
        return jsonify({'success': True, 'comments': comments})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@routes_bp.route('/api/comments', methods=['POST'])
def add_comment():
    """Add a new comment."""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('name') or not data.get('comment'):
            return jsonify({'success': False, 'message': 'Name and comment are required'}), 400

        # Create comment object
        comment = {
            'name': data.get('name'),
            'email': data.get('email', ''),
            'comment': data.get('comment'),
            'rating': data.get('rating', 5),
            'approved': False,  # Comments need approval
            'created_at': datetime.now()
        }

        # Insert comment
        result = db.comments.insert_one(comment)

        if result.inserted_id:
            return jsonify({'success': True, 'message': 'Thank you for your comment! It will be reviewed before being published.'})
        else:
            return jsonify({'success': False, 'message': 'Failed to add comment'}), 500

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# --- Customer Dashboard and Profile Routes ---

@routes_bp.route('/customer/dashboard')
@login_required
def customer_dashboard():
    """Customer dashboard with order history and statistics."""
    try:
        # Get customer's orders
        customer_orders = list(db.orders.find({'customer_email': current_user.email}).sort('created_at', -1).limit(5))
        for order in customer_orders:
            order['_id'] = str(order['_id'])
        
        # Get customer's cart items
        cart_items = list(db.carts.find({'user_email': current_user.email}))
        for item in cart_items:
            item['_id'] = str(item['_id'])
        
        # Calculate statistics
        total_orders = db.orders.count_documents({'customer_email': current_user.email})
        total_spent = sum(order.get('total_amount', 0) for order in customer_orders)
        
        # Get recent wishlist items (if wishlist collection exists)
        wishlist_items = []
        if 'wishlist' in db.list_collection_names():
            wishlist_items = list(db.wishlist.find({'user_email': current_user.email}).limit(3))
            for item in wishlist_items:
                item['_id'] = str(item['_id'])
        
        # Get loyalty points (if loyalty collection exists)
        loyalty_points = 0
        if 'loyalty_points' in db.list_collection_names():
            loyalty_doc = db.loyalty_points.find_one({'customer_email': current_user.email})
            if loyalty_doc:
                loyalty_points = loyalty_doc.get('points', 0)
        
        return render_template('customer_dashboard.html', 
                             orders=customer_orders,
                             cart_items=cart_items,
                             wishlist_items=wishlist_items,
                             total_orders=total_orders,
                             total_spent=total_spent,
                             loyalty_points=loyalty_points)
    except Exception as e:
        print(f"Error loading customer dashboard: {e}")
        # Return empty data if there's an error
        return render_template('customer_dashboard.html', 
                             orders=[],
                             cart_items=[],
                             wishlist_items=[],
                             total_orders=0,
                             total_spent=0,
                             loyalty_points=0)

@routes_bp.route('/customer/profile', methods=['GET', 'POST'])
@login_required
def customer_profile():
    """Customer profile management page."""
    if request.method == 'POST':
        try:
            # Update user profile
            update_data = {
                'first_name': request.form.get('first_name'),
                'last_name': request.form.get('last_name'),
                'email': request.form.get('email'),
                'phone': request.form.get('phone'),
                'address': request.form.get('address'),
                'city': request.form.get('city'),
                'district': request.form.get('district'),
                'postal_code': request.form.get('postal_code'),
                'is_student': request.form.get('is_student') == 'true',
                'newsletter': request.form.get('newsletter') == 'true'
            }
            
            # Handle password change if provided
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if current_password and new_password:
                if new_password != confirm_password:
                    flash('New passwords do not match!', 'error')
                    return render_template('customer_profile.html')
                
                if not check_password_hash(current_user.password, current_password):
                    flash('Current password is incorrect!', 'error')
                    return render_template('customer_profile.html')
                
                update_data['password'] = generate_password_hash(new_password)
            
            # Update user in database
            db.users.update_one(
                {'_id': current_user._id},
                {'$set': update_data}
            )
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('routes.customer_profile'))
            
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'error')
    
    return render_template('customer_profile.html')

@routes_bp.route('/wishlist/add', methods=['POST'])
@login_required
def add_to_wishlist():
    """Add a cake to the user's wishlist."""
    try:
        data = request.get_json()
        cake_id = data.get('cake_id')
        cake_name = data.get('cake_name')
        cake_price = data.get('cake_price')
        cake_image = data.get('cake_image')
        
        # Check if already in wishlist
        existing = db.wishlist.find_one({
            'user_email': current_user.email,
            'cake_id': cake_id
        })
        
        if existing:
            return jsonify({'success': False, 'message': 'Cake already in wishlist'})
        
        # Add to wishlist
        wishlist_item = {
            'user_email': current_user.email,
            'cake_id': cake_id,
            'cake_name': cake_name,
            'cake_price': cake_price,
            'cake_image': cake_image,
            'added_at': datetime.now()
        }
        
        db.wishlist.insert_one(wishlist_item)
        return jsonify({'success': True, 'message': 'Added to wishlist'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@routes_bp.route('/wishlist/remove', methods=['POST'])
@login_required
def remove_from_wishlist():
    """Remove a cake from the user's wishlist."""
    try:
        data = request.get_json()
        cake_id = data.get('cake_id')
        
        result = db.wishlist.delete_one({
            'user_email': current_user.email,
            'cake_id': cake_id
        })
        
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Removed from wishlist'})
        else:
            return jsonify({'success': False, 'message': 'Item not found in wishlist'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@routes_bp.route('/wishlist')
@login_required
def wishlist_page():
    """Display the user's wishlist page."""
    try:
        # Get user's wishlist items
        wishlist_items = list(db.wishlist.find({'user_email': current_user.email}).sort('added_at', -1))
        for item in wishlist_items:
            item['_id'] = str(item['_id'])
        
        return render_template('wishlist.html', wishlist_items=wishlist_items)
    except Exception as e:
        print(f"Error loading wishlist: {e}")
        return render_template('wishlist.html', wishlist_items=[])

@routes_bp.route('/customer/orders')
@login_required
def order_history():
    """Customer order history page."""
    try:
        # Get customer's orders
        customer_orders = list(db.orders.find({'customer_email': current_user.email}).sort('created_at', -1))
        for order in customer_orders:
            order['_id'] = str(order['_id'])
        
        # Calculate statistics
        total_orders = len(customer_orders)
        total_spent = sum(order.get('total_amount', 0) for order in customer_orders)
        
        # Get order status counts
        status_counts = {
            'pending': len([o for o in customer_orders if o.get('status') == 'pending']),
            'processing': len([o for o in customer_orders if o.get('status') == 'processing']),
            'completed': len([o for o in customer_orders if o.get('status') == 'completed']),
            'cancelled': len([o for o in customer_orders if o.get('status') == 'cancelled'])
        }
        
        return render_template('order_history.html', 
                             orders=customer_orders,
                             total_orders=total_orders,
                             total_spent=total_spent,
                             status_counts=status_counts)
    except Exception as e:
        print(f"Error loading order history: {e}")
        # Return empty data if there's an error
        return render_template('order_history.html', 
                             orders=[],
                             total_orders=0,
                             total_spent=0,
                             status_counts={'pending': 0, 'processing': 0, 'completed': 0, 'cancelled': 0})
