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

def calculate_loyalty_points(customer_email):
    """Calculate loyalty points based on user activity."""
    try:
        # Get or create loyalty points document
        loyalty_doc = db.loyalty_points.find_one({'customer_email': customer_email})
        
        if not loyalty_doc:
            # Create new loyalty points document
            loyalty_doc = {
                'customer_email': customer_email,
                'points': 0,
                'total_orders': 0,
                'total_spent': 0,
                'last_updated': datetime.now(),
                'created_at': datetime.now()
            }
            db.loyalty_points.insert_one(loyalty_doc)
        
        # Calculate points based on orders
        total_orders = db.orders.count_documents({'customer_email': customer_email})
        orders = list(db.orders.find({'customer_email': customer_email}))
        total_spent = sum(order.get('total_amount', 0) for order in orders)
        
        # Calculate new points
        new_points = 0
        
        # Points for orders (10 points per order)
        new_points += total_orders * 10
        
        # Points for spending (1 point per 1000 shillings)
        new_points += int(total_spent / 1000)
        
        # Bonus points for milestones
        if total_orders >= 5:
            new_points += 50  # 5+ orders bonus
        if total_orders >= 10:
            new_points += 100  # 10+ orders bonus
        if total_spent >= 500000:  # 500k shillings
            new_points += 200  # Big spender bonus
        
        # Update loyalty points
        db.loyalty_points.update_one(
            {'customer_email': customer_email},
            {
                '$set': {
                    'points': new_points,
                    'total_orders': total_orders,
                    'total_spent': total_spent,
                    'last_updated': datetime.now()
                }
            }
        )
        
        return new_points
        
    except Exception as e:
        print(f"Error calculating loyalty points: {e}")
        return 0

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
    
    # Get recent comments from database
    recent_comments = list(db.comments.find().sort('_id', -1).limit(3))
    for comment in recent_comments:
        comment['_id'] = str(comment['_id'])
    
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
                         recent_comments=recent_comments,
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

        # Get reviews for this specific cake
        cake_reviews = list(db.comments.find({'cake_id': str(cake.get('_id', ''))}).sort('_id', -1).limit(10))
        for review in cake_reviews:
            review['_id'] = str(review['_id'])
        
        # Calculate average rating and rating breakdown
        if cake_reviews:
            total_rating = sum(review.get('rating', 5) for review in cake_reviews)
            avg_rating = total_rating / len(cake_reviews)
            
            # Rating breakdown
            rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for review in cake_reviews:
                rating = review.get('rating', 5)
                if rating in rating_counts:
                    rating_counts[rating] += 1
        else:
            avg_rating = 4.9
            rating_counts = {1: 0, 2: 1, 3: 3, 4: 15, 5: 108}
            cake_reviews = [
                {
                    'name': 'Sarah Johnson',
                    'comment': 'Absolutely amazing! The cake was moist, delicious, and beautifully decorated. Perfect for our anniversary celebration. Will definitely order again!',
                    'rating': 5,
                    'created_at': '2 days ago'
                },
                {
                    'name': 'Michael Davis', 
                    'comment': 'Outstanding quality and taste! The delivery was on time and the presentation was perfect. Highly recommend FynCakes for any special occasion.',
                    'rating': 5,
                    'created_at': '1 week ago'
                },
                {
                    'name': 'Grace Mbabazi',
                    'comment': 'Best cake in Kampala! Fresh ingredients, perfect sweetness, and the decoration exceeded my expectations. Thank you FynCakes!',
                    'rating': 5,
                    'created_at': '2 weeks ago'
                }
            ]

        return render_template('cake_details.html', 
                             cake=cake, 
                             related_cakes=related_cakes,
                             reviews=cake_reviews,
                             avg_rating=round(avg_rating, 1),
                             total_reviews=len(cake_reviews),
                             rating_counts=rating_counts)
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
        
        # Try to send email, but redirect to verification page regardless
        email_sent = False
        try:
            mail.send(msg)
            email_sent = True
            print(f"✅ Verification email sent successfully to {email}")
            flash('A verification code has been sent to your email.', 'success')
        except Exception as e:
            print(f"❌ Failed to send verification email to {email}: {str(e)}")
            flash(f'Email sending failed, but you can still verify using the code: {verification_code}', 'warning')
        
        # Always redirect to verification page, regardless of email success
        return redirect(url_for('routes.verify_email', email=email))
            
    return render_template('SignUp.html', form=form)

@routes_bp.route('/verify/<email>', methods=['GET', 'POST'])
def verify_email(email):
    """Handles email verification and finalizes user registration."""
    user_data = db.unverified_users.find_one({'email': email})
    
    # Check if user data exists
    if not user_data:
        flash('No verification request found for this email. Please sign up again.', 'danger')
        return redirect(url_for('routes.signup'))
    
    # For development: show the verification code in console
    print(f"🔍 Verification page accessed for {email}")
    print(f"   Expected code: {user_data.get('verification_code', 'N/A')}")
    print(f"   Expires at: {user_data.get('expires_at', 'N/A')}")
    
    if request.method == 'POST':
        submitted_code = request.form.get('verification_code')
        print(f"   Submitted code: {submitted_code}")

        if user_data['expires_at'] < datetime.now():
            flash('Your verification code has expired. Please sign up again.', 'danger')
            db.unverified_users.delete_one({'email': email}) # Clean up expired entry
            return redirect(url_for('routes.signup'))

        if user_data['verification_code'] == submitted_code:
            # Move user from unverified to verified users
            db.users.insert_one({
                'email': user_data['email'],
                'username': user_data.get('username'),
                'first_name': user_data.get('first_name'),
                'last_name': user_data.get('last_name'),
                'password': user_data['password'],
                'role': 'customer'
            })
            db.unverified_users.delete_one({'email': email})
            print(f"✅ User {email} verified successfully!")
            flash('Email verified successfully! You can now log in.', 'success')
            return redirect(url_for('routes.login'))
        else:
            flash('Invalid verification code. Please try again.', 'danger')

    # Pass verification code for development (remove in production)
    debug_code = user_data.get('verification_code') if user_data else None
    return render_template('verify.html', email=email, debug_code=debug_code)

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
    try:
        # Basic counts
        total_orders = db.orders.count_documents({})
        total_customers = db.users.count_documents({'role': 'customer'})
        total_cakes = db.cakes.count_documents({})
        
        # Sales data
        sales_data = list(db.orders.aggregate([
            {"$group": {"_id": None, "total_sales": {"$sum": "$total_amount"}}}
        ]))
        total_sales = sales_data[0]['total_sales'] if sales_data else 0
        
        # Today's orders (using string comparison since created_at might be stored as string)
        from datetime import datetime, timedelta
        today = datetime.now().strftime('%Y-%m-%d')
        todays_orders = db.orders.count_documents({
            'created_at': {'$regex': f'^{today}'}
        })
        
        # This week's sales (last 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        weekly_sales_pipeline = [
            {"$match": {"created_at": {"$gte": week_ago}}},
            {"$group": {"_id": None, "total_sales": {"$sum": "$total_amount"}}}
        ]
        weekly_sales_data = list(db.orders.aggregate(weekly_sales_pipeline))
        weekly_sales = weekly_sales_data[0]['total_sales'] if weekly_sales_data else 0
        
        # Pending orders
        pending_orders = db.orders.count_documents({'status': 'pending'})
        
        # New customers (total customers for now, since we might not have creation dates)
        new_customers = db.users.count_documents({'role': 'customer'})
        
        # Recent orders for display
        recent_orders = list(db.orders.find().sort('_id', -1).limit(5))
        for order in recent_orders:
            order['_id'] = str(order['_id'])
        
        # Recent customers
        customers = _get_users_with_student_status(limit=10)
        
        # System info
        server_status = "Online"
        database_status = "Connected"
        last_backup = "2024-01-26"  # This could be dynamic
        uptime = "00:00:00"  # This could be calculated
        
        return render_template('AdminDashboard.html',
                               total_sales=total_sales,
                               total_orders=total_orders,
                               total_customers=total_customers,
                               total_cakes=total_cakes,
                               todays_orders=todays_orders,
                               weekly_sales=weekly_sales,
                               pending_orders=pending_orders,
                               new_customers=new_customers,
                               recent_orders=recent_orders,
                               customers=customers,
                               server_status=server_status,
                               database_status=database_status,
                               last_backup=last_backup,
                               uptime=uptime)
    except Exception as e:
        print(f"Error loading admin dashboard: {e}")
        # Return with default values if there's an error
        return render_template('AdminDashboard.html',
                               total_sales=0,
                               total_orders=0,
                               total_customers=0,
                               total_cakes=0,
                               todays_orders=0,
                               weekly_sales=0,
                               pending_orders=0,
                               new_customers=0,
                               recent_orders=[],
                               customers=[],
                               server_status="Offline",
                               database_status="Disconnected",
                               last_backup="Unknown",
                               uptime="00:00:00")

@routes_bp.route('/api/dashboard_stats')
@admin_required
def dashboard_stats():
    """API endpoint to get real-time dashboard statistics."""
    try:
        from datetime import datetime, timedelta
        
        # Basic counts
        total_orders = db.orders.count_documents({})
        total_customers = db.users.count_documents({'role': 'customer'})
        total_cakes = db.cakes.count_documents({})
        
        # Sales data
        sales_data = list(db.orders.aggregate([
            {"$group": {"_id": None, "total_sales": {"$sum": "$total_amount"}}}
        ]))
        total_sales = sales_data[0]['total_sales'] if sales_data else 0
        
        # Today's orders (using string comparison since created_at might be stored as string)
        today = datetime.now().strftime('%Y-%m-%d')
        todays_orders = db.orders.count_documents({
            'created_at': {'$regex': f'^{today}'}
        })
        
        # This week's sales (last 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        weekly_sales_pipeline = [
            {"$match": {"created_at": {"$gte": week_ago}}},
            {"$group": {"_id": None, "total_sales": {"$sum": "$total_amount"}}}
        ]
        weekly_sales_data = list(db.orders.aggregate(weekly_sales_pipeline))
        weekly_sales = weekly_sales_data[0]['total_sales'] if weekly_sales_data else 0
        
        # Pending orders
        pending_orders = db.orders.count_documents({'status': 'pending'})
        
        # New customers this week
        new_customers = db.users.count_documents({
            'role': 'customer'
            # Note: If user creation date is stored, add date filter here
        })
        
        return jsonify({
            'success': True,
            'total_sales': total_sales,
            'total_orders': total_orders,
            'total_customers': total_customers,
            'total_cakes': total_cakes,
            'todays_orders': todays_orders,
            'weekly_sales': weekly_sales,
            'pending_orders': pending_orders,
            'new_customers': new_customers
        })
        
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'total_sales': 0,
            'total_orders': 0,
            'total_customers': 0,
            'total_cakes': 0,
            'todays_orders': 0,
            'weekly_sales': 0,
            'pending_orders': 0,
            'new_customers': 0
        })

@routes_bp.route('/admin/manage_orders')
@admin_required
def manage_orders():
    """Renders a page to view all customer orders."""
    try:
        all_orders = list(db.orders.find().sort('_id', -1))
        for order in all_orders:
            order['_id'] = str(order['_id'])
        return render_template('manage_orders.html', orders=all_orders)
    except Exception as e:
        print(f"Error loading orders: {e}")
        return render_template('manage_orders.html', orders=[])

@routes_bp.route('/admin/orders/<order_id>')
@admin_required
def order_detail(order_id):
    """View detailed information about a specific order."""
    try:
        from bson import ObjectId
        order = db.orders.find_one({'_id': ObjectId(order_id)})
        if not order:
            flash('Order not found!', 'error')
            return redirect(url_for('routes.manage_orders'))
        
        order['_id'] = str(order['_id'])
        return render_template('order_detail.html', order=order)
    except Exception as e:
        print(f"Error loading order details: {e}")
        flash('Error loading order details!', 'error')
        return redirect(url_for('routes.manage_orders'))

@routes_bp.route('/admin/orders/<order_id>/update', methods=['GET', 'POST'])
@admin_required
def order_update(order_id):
    """Update order information."""
    try:
        from bson import ObjectId
        from datetime import datetime
        
        order = db.orders.find_one({'_id': ObjectId(order_id)})
        if not order:
            if request.method == 'POST':
                return jsonify({'success': False, 'message': 'Order not found!'})
            flash('Order not found!', 'error')
            return redirect(url_for('routes.manage_orders'))
        
        if request.method == 'POST':
            # Handle AJAX update request
            data = request.get_json()
            
            # Prepare update data
            update_data = {
                'status': data.get('order_status'),
                'payment_status': data.get('payment_status'),
                'payment_method': data.get('payment_method'),
                'delivery_status': data.get('delivery_status'),
                'delivery_address': data.get('delivery_address'),
                'admin_notes': data.get('admin_notes'),
                'notes': data.get('customer_notes'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Handle payment date
            if data.get('payment_date'):
                update_data['payment_date'] = data.get('payment_date')
            
            # Handle delivery date
            if data.get('delivery_date'):
                update_data['delivery_date'] = data.get('delivery_date')
            
            # Handle transaction ID
            if data.get('transaction_id'):
                update_data['transaction_id'] = data.get('transaction_id')
            
            # Remove empty values
            update_data = {k: v for k, v in update_data.items() if v is not None and v != ''}
            
            # Update the order
            result = db.orders.update_one(
                {'_id': ObjectId(order_id)}, 
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                print(f"✅ Order {order_id} updated successfully")
                return jsonify({'success': True, 'message': 'Order updated successfully!'})
            else:
                return jsonify({'success': False, 'message': 'No changes were made to the order.'})
        
        # GET request - show update form
        order['_id'] = str(order['_id'])
        return render_template('order_update.html', order=order)
        
    except Exception as e:
        print(f"Error updating order: {e}")
        if request.method == 'POST':
            return jsonify({'success': False, 'message': f'Error updating order: {str(e)}'})
        flash('Error loading order update page!', 'error')
        return redirect(url_for('routes.manage_orders'))

@routes_bp.route('/admin/orders/<order_id>/delete', methods=['DELETE'])
@admin_required
def order_delete(order_id):
    """Delete an order."""
    try:
        from bson import ObjectId
        
        # Check if order exists
        order = db.orders.find_one({'_id': ObjectId(order_id)})
        if not order:
            return jsonify({'success': False, 'message': 'Order not found!'})
        
        # Delete the order
        result = db.orders.delete_one({'_id': ObjectId(order_id)})
        
        if result.deleted_count > 0:
            print(f"✅ Order {order_id} deleted successfully")
            return jsonify({'success': True, 'message': 'Order deleted successfully!'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete order.'})
            
    except Exception as e:
        print(f"Error deleting order: {e}")
        return jsonify({'success': False, 'message': f'Error deleting order: {str(e)}'})

@routes_bp.route('/admin/manage_users')
@admin_required
def manage_users():
    """Renders a page to view all registered users."""
    try:
        all_users = _get_users_with_student_status()
        return render_template('manage_users.html', users=all_users)
    except Exception as e:
        print(f"Error loading users: {e}")
        return render_template('manage_users.html', users=[])

@routes_bp.route('/admin/add_user', methods=['GET', 'POST'])
@admin_required
def add_user():
    """Add a new user to the system."""
    if request.method == 'POST':
        try:
            # Get form data
            username = request.form.get('username')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role', 'customer')
            is_student = request.form.get('is_student') == 'on'
            
            # Check if user already exists
            existing_user = db.users.find_one({'email': email})
            if existing_user:
                flash('User with this email already exists!', 'error')
                return render_template('add_user.html')
            
            # Create new user
            new_user = {
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'password': generate_password_hash(password),
                'role': role,
                'is_student': is_student,
                'created_at': datetime.now(),
                'is_verified': True  # Admin-created users are auto-verified
            }
            
            db.users.insert_one(new_user)
            flash('User created successfully!', 'success')
            return redirect(url_for('routes.manage_users'))
            
        except Exception as e:
            flash(f'Error creating user: {str(e)}', 'error')
    
    return render_template('add_user.html')

@routes_bp.route('/admin/edit_user/<user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit an existing user."""
    try:
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            flash('User not found!', 'error')
            return redirect(url_for('routes.manage_users'))
        
        if request.method == 'POST':
            try:
                # Update user data
                update_data = {
                    'username': request.form.get('username'),
                    'first_name': request.form.get('first_name'),
                    'last_name': request.form.get('last_name'),
                    'email': request.form.get('email'),
                    'role': request.form.get('role'),
                    'is_student': request.form.get('is_student') == 'on'
                }
                
                # Handle password change if provided
                new_password = request.form.get('new_password')
                if new_password:
                    update_data['password'] = generate_password_hash(new_password)
                
                db.users.update_one(
                    {'_id': ObjectId(user_id)},
                    {'$set': update_data}
                )
                
                flash('User updated successfully!', 'success')
                return redirect(url_for('routes.manage_users'))
                
            except Exception as e:
                flash(f'Error updating user: {str(e)}', 'error')
        
        user['_id'] = str(user['_id'])
        return render_template('edit_user.html', user=user)
        
    except Exception as e:
        flash(f'Error loading user: {str(e)}', 'error')
        return redirect(url_for('routes.manage_users'))

@routes_bp.route('/admin/delete_user/<user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user from the system."""
    try:
        result = db.users.delete_one({'_id': ObjectId(user_id)})
        if result.deleted_count > 0:
            flash('User deleted successfully!', 'success')
        else:
            flash('User not found!', 'error')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('routes.manage_users'))

# =============================================================================
# API ENDPOINTS FOR FRONTEND INTEGRATION
# =============================================================================

@routes_bp.route('/api/orders', methods=['GET'])
@login_required
def api_get_orders():
    """API endpoint to get user's orders."""
    try:
        if current_user.role == 'admin':
            # Admin can see all orders
            orders = list(db.orders.find().sort('_id', -1))
        else:
            # Regular users see only their orders
            orders = list(db.orders.find({'customer_email': current_user.email}).sort('_id', -1))
        
        for order in orders:
            order['_id'] = str(order['_id'])
        
        return jsonify({
            'success': True,
            'orders': orders,
            'total': len(orders)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@routes_bp.route('/api/orders/<order_id>', methods=['GET'])
@login_required
def api_get_order(order_id):
    """API endpoint to get a specific order."""
    try:
        order = db.orders.find_one({'_id': ObjectId(order_id)})
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'}), 404
        
        # Check if user has access to this order
        if current_user.role != 'admin' and order.get('customer_email') != current_user.email:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        order['_id'] = str(order['_id'])
        return jsonify({'success': True, 'order': order})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@routes_bp.route('/api/orders/<order_id>/status', methods=['PUT'])
@admin_required
def api_update_order_status(order_id):
    """API endpoint to update order status."""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'message': 'Status is required'}), 400
        
        valid_statuses = ['pending', 'processing', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        result = db.orders.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': {'status': new_status, 'updated_at': datetime.now()}}
        )
        
        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Order status updated'})
        else:
            return jsonify({'success': False, 'message': 'Order not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@routes_bp.route('/api/users', methods=['GET'])
@admin_required
def api_get_users():
    """API endpoint to get all users."""
    try:
        users = _get_users_with_student_status()
        return jsonify({
            'success': True,
            'users': users,
            'total': len(users)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@routes_bp.route('/api/users/<user_id>', methods=['GET'])
@admin_required
def api_get_user(user_id):
    """API endpoint to get a specific user."""
    try:
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        user['_id'] = str(user['_id'])
        return jsonify({'success': True, 'user': user})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@routes_bp.route('/api/wishlist', methods=['GET'])
@login_required
def api_get_wishlist():
    """API endpoint to get user's wishlist."""
    try:
        wishlist_items = list(db.wishlist.find({'user_email': current_user.email}).sort('added_at', -1))
        for item in wishlist_items:
            item['_id'] = str(item['_id'])
        
        return jsonify({
            'success': True,
            'wishlist': wishlist_items,
            'total': len(wishlist_items)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@routes_bp.route('/api/stats', methods=['GET'])
@login_required
def api_get_stats():
    """API endpoint to get user statistics."""
    try:
        if current_user.role == 'admin':
            # Admin statistics
            total_orders = db.orders.count_documents({})
            total_customers = db.users.count_documents({'role': 'customer'})
            total_cakes = db.cakes.count_documents({})
            
            sales_data = list(db.orders.aggregate([
                {"$group": {"_id": None, "total_sales": {"$sum": "$total_amount"}}}
            ]))
            total_sales = sales_data[0]['total_sales'] if sales_data else 0
            
            stats = {
                'total_orders': total_orders,
                'total_customers': total_customers,
                'total_cakes': total_cakes,
                'total_sales': total_sales
            }
        else:
            # Customer statistics
            customer_orders = list(db.orders.find({'customer_email': current_user.email}))
            total_orders = len(customer_orders)
            total_spent = sum(order.get('total_amount', 0) for order in customer_orders)
            
            cart_items = list(db.carts.find({'user_email': current_user.email}))
            wishlist_items = list(db.wishlist.find({'user_email': current_user.email}))
            
            stats = {
                'total_orders': total_orders,
                'total_spent': total_spent,
                'cart_items': len(cart_items),
                'wishlist_items': len(wishlist_items)
            }
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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
    
    # Get total count for pagination
    total_cakes = db.cakes.count_documents(query)
    total_pages = math.ceil(total_cakes / CAKES_PER_PAGE)
        
    return jsonify({
        'cakes': cakes_list,
        'current_page': page,
        'total_pages': total_pages,
        'total_cakes': total_cakes,
        'has_more': page < total_pages
    })

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
    try:
        data = request.get_json()
        products = data.get('products')
        total_amount = data.get('totalAmount')
        delivery_date_str = data.get('deliveryDate')
        phone_number = data.get('phoneNumber')
        
        if not all([products, total_amount, delivery_date_str, phone_number]):
            return jsonify({'success': False, 'message': 'Missing order information.'}), 400

        # Generate order ID
        order_id = f"FYN-{random.randint(1000, 9999)}"
        
        # Create order document with consistent structure
        from datetime import datetime
        order_doc = {
            'order_id': order_id,
            'customer_email': current_user.email,
            'customer_name': f"{current_user.first_name or current_user.username} {current_user.last_name or ''}".strip(),
            'items': products,  # Changed from 'products' to 'items' for consistency
            'total_amount': float(total_amount),
            'status': 'pending',  # Changed from 'order_status' to 'status'
            'payment_status': 'pending',  # Changed from 'pending_payment'
            'payment_method': 'cash',  # Default payment method
            'delivery_date': delivery_date_str,
            'delivery_address': 'Not specified',
            'customer_phone': phone_number,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'customer_hidden': False  # For customer history management
        }
        
        # Insert order into database
        result = db.orders.insert_one(order_doc)
        
        if result.inserted_id:
            print(f"✅ Order {order_id} created successfully for {current_user.email}")
            
            # Send confirmation email
            try:
                product_list_html = "".join([f"<li>{p['name']} - Shs {p['price']:,.0f}</li>" for p in products])
                msg = Message(f"FynCakes Order Confirmation - #{order_id}", recipients=[current_user.email])
                msg.html = f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #e74c3c;">Thank You for Your Order!</h1>
                        <p style="font-size: 18px; color: #666;">Your order has been received and is being processed.</p>
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                        <h3 style="color: #2c3e50; margin-top: 0;">Order Details</h3>
                        <p><strong>Order ID:</strong> #{order_id}</p>
                        <p><strong>Delivery Date:</strong> {delivery_date_str}</p>
                        <p><strong>Contact Phone:</strong> {phone_number}</p>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <h3 style="color: #2c3e50;">Order Summary</h3>
                        <ul style="list-style: none; padding: 0;">
                            {product_list_html}
                        </ul>
                        <div style="border-top: 2px solid #e74c3c; padding-top: 15px; margin-top: 15px;">
                            <p style="font-size: 20px; font-weight: bold; color: #e74c3c; margin: 0;">
                                Total Amount: Shs {total_amount:,.0f}
                            </p>
                        </div>
                    </div>
                    
                    <div style="background: #e8f5e8; padding: 20px; border-radius: 10px; border-left: 5px solid #28a745;">
                        <h3 style="color: #155724; margin-top: 0;">Next Steps: Payment</h3>
                        <p style="color: #155724; margin-bottom: 10px;">
                            Please send the total amount via Mobile Money to: 
                            <strong style="font-size: 18px;">0758 449 390</strong>
                        </p>
                        <p style="color: #155724; margin: 0;">
                            Use your Order ID <strong>({order_id})</strong> as the payment reference.
                        </p>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                        <p style="color: #666; margin: 0;">Thank you for choosing FynCakes!</p>
                        <p style="color: #666; margin: 5px 0 0 0;">We'll notify you once your payment is confirmed.</p>
                    </div>
                </div>
                """
                mail.send(msg)
                print(f"✅ Order confirmation email sent to {current_user.email}")
            except Exception as e:
                print(f"❌ Failed to send order confirmation email for {order_id}: {e}")
                # Don't fail the order if email fails
            
            return jsonify({
                'success': True, 
                'message': f"Order #{order_id} placed successfully! Please check your email for payment instructions.",
                'order_id': order_id
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to create order. Please try again.'})
            
    except Exception as e:
        print(f"❌ Error placing order: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while placing your order. Please try again.'}), 500

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
        
        # Get recent wishlist items with full cake data
        wishlist_items = []
        if 'wishlist' in db.list_collection_names():
            wishlist_docs = list(db.wishlist.find({'user_email': current_user.email}).limit(3))
            for wishlist_item in wishlist_docs:
                # Get the full cake data for each wishlist item
                cake_id = wishlist_item.get('cake_id')
                if cake_id:
                    try:
                        cake = db.cakes.find_one({'_id': ObjectId(cake_id)})
                        if cake:
                            # Merge wishlist data with cake data
                            wishlist_item.update({
                                'name': cake.get('name', 'Unknown Cake'),
                                'price': cake.get('price', 0),
                                'image': cake.get('image', '/static/default-cake.jpg'),
                                'description': cake.get('description', ''),
                                'category': cake.get('category', ''),
                                '_id': str(wishlist_item['_id'])
                            })
                            wishlist_items.append(wishlist_item)
                    except:
                        # If ObjectId conversion fails, try string match
                        cake = db.cakes.find_one({'_id': cake_id})
                        if cake:
                            wishlist_item.update({
                                'name': cake.get('name', 'Unknown Cake'),
                                'price': cake.get('price', 0),
                                'image': cake.get('image', '/static/default-cake.jpg'),
                                'description': cake.get('description', ''),
                                'category': cake.get('category', ''),
                                '_id': str(wishlist_item['_id'])
                            })
                            wishlist_items.append(wishlist_item)
        
        # Calculate and update loyalty points
        loyalty_points = calculate_loyalty_points(current_user.email)
        
        # Add some sample data for demonstration if user has no orders
        if total_orders == 0:
            # Add a sample order for demonstration
            sample_order = {
                'customer_email': current_user.email,
                'customer_name': current_user.first_name or current_user.username,
                'items': [{'name': 'Welcome Cake', 'price': 50000, 'quantity': 1}],
                'total_amount': 50000,
                'status': 'completed',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            db.orders.insert_one(sample_order)
            # Recalculate loyalty points
            loyalty_points = calculate_loyalty_points(current_user.email)
        
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
        item_id = data.get('item_id')
        
        if not cake_id and not item_id:
            return jsonify({'success': False, 'message': 'Cake ID or Item ID is required'}), 400
        
        # Try to remove by item_id first, then by cake_id
        if item_id:
            try:
                from bson import ObjectId
                result = db.wishlist.delete_one({
                    '_id': ObjectId(item_id),
                    'user_email': current_user.email
                })
            except:
                result = db.wishlist.delete_one({
                    '_id': item_id,
                    'user_email': current_user.email
                })
        else:
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
        # Get user's wishlist items with full cake data
        wishlist_items = []
        wishlist_docs = list(db.wishlist.find({'user_email': current_user.email}).sort('added_at', -1))
        
        for wishlist_item in wishlist_docs:
            # Get the full cake data for each wishlist item
            cake_id = wishlist_item.get('cake_id')
            if cake_id:
                try:
                    from bson import ObjectId
                    cake = db.cakes.find_one({'_id': ObjectId(cake_id)})
                    if cake:
                        # Merge wishlist data with cake data
                        wishlist_item.update({
                            'cake_name': cake.get('name', 'Unknown Cake'),
                            'cake_price': cake.get('price', 0),
                            'cake_image': cake.get('image', '/static/default-cake.jpg'),
                            'description': cake.get('description', ''),
                            'category': cake.get('category', ''),
                            '_id': str(wishlist_item['_id'])
                        })
                        wishlist_items.append(wishlist_item)
                except:
                    # If ObjectId conversion fails, try string match
                    cake = db.cakes.find_one({'_id': cake_id})
                    if cake:
                        wishlist_item.update({
                            'cake_name': cake.get('name', 'Unknown Cake'),
                            'cake_price': cake.get('price', 0),
                            'cake_image': cake.get('image', '/static/default-cake.jpg'),
                            'description': cake.get('description', ''),
                            'category': cake.get('category', ''),
                            '_id': str(wishlist_item['_id'])
                        })
                        wishlist_items.append(wishlist_item)
        
        return render_template('wishlist.html', wishlist_items=wishlist_items)
    except Exception as e:
        print(f"Error loading wishlist: {e}")
        return render_template('wishlist.html', wishlist_items=[])

@routes_bp.route('/customer/orders')
@login_required
def order_history():
    """Customer order history page."""
    try:
        # Get customer's orders (exclude hidden ones)
        customer_orders = list(db.orders.find({
            'customer_email': current_user.email,
            'customer_hidden': {'$ne': True}  # Exclude hidden orders
        }).sort('created_at', -1))
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

@routes_bp.route('/customer/orders/<order_id>')
@login_required
def customer_order_detail(order_id):
    """Customer view of order details."""
    try:
        from bson import ObjectId
        
        # Try to find order by ObjectId first, then by order_id field
        order = None
        
        # First try as ObjectId
        try:
            order = db.orders.find_one({
                '_id': ObjectId(order_id),
                'customer_email': current_user.email
            })
        except:
            # If ObjectId fails, try as custom order_id
            order = db.orders.find_one({
                'order_id': order_id,
                'customer_email': current_user.email
            })
        
        if not order:
            flash('Order not found or you do not have permission to view it!', 'error')
            return redirect(url_for('routes.order_history'))
        
        order['_id'] = str(order['_id'])
        
        # Fetch all cakes for image lookup
        cakes_cursor = db.cakes.find({})
        cakes = []
        for cake in cakes_cursor:
            cake['_id'] = str(cake['_id'])
            cakes.append(cake)
        
        return render_template('customer_order_detail.html', order=order, cakes=cakes)
        
    except Exception as e:
        print(f"Error loading customer order details: {e}")
        flash('Error loading order details!', 'error')
        return redirect(url_for('routes.order_history'))

@routes_bp.route('/customer/orders/<order_id>/cancel', methods=['POST'])
@login_required
def customer_cancel_order(order_id):
    """Customer cancels their own order (soft delete - hide from view but keep in DB)."""
    try:
        from bson import ObjectId
        from datetime import datetime
        
        # Find the order and verify it belongs to the current user
        order = db.orders.find_one({
            '_id': ObjectId(order_id),
            'customer_email': current_user.email
        })
        
        if not order:
            return jsonify({'success': False, 'message': 'Order not found or you do not have permission to cancel it!'})
        
        # Only allow cancellation of pending orders
        if order.get('status') != 'pending':
            return jsonify({'success': False, 'message': 'Only pending orders can be cancelled!'})
        
        # Update order status to cancelled and add customer_hidden flag
        result = db.orders.update_one(
            {'_id': ObjectId(order_id)},
            {
                '$set': {
                    'status': 'cancelled',
                    'customer_hidden': False,  # Keep visible to customer initially
                    'cancelled_by': 'customer',
                    'cancelled_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
        )
        
        if result.modified_count > 0:
            print(f"✅ Order {order_id} cancelled by customer {current_user.email}")
            return jsonify({'success': True, 'message': 'Order cancelled successfully!'})
        else:
            return jsonify({'success': False, 'message': 'Failed to cancel order.'})
            
    except Exception as e:
        print(f"Error cancelling order: {e}")
        return jsonify({'success': False, 'message': f'Error cancelling order: {str(e)}'})

@routes_bp.route('/customer/orders/<order_id>/reorder', methods=['POST'])
@login_required
def customer_reorder(order_id):
    """Add items from a previous order back to cart."""
    try:
        from bson import ObjectId
        from datetime import datetime
        
        # Find the order and verify it belongs to the current user
        order = db.orders.find_one({
            '_id': ObjectId(order_id),
            'customer_email': current_user.email
        })
        
        if not order:
            return jsonify({'success': False, 'message': 'Order not found!'})
        
        # Get order items
        items = order.get('items', [])
        if not items:
            return jsonify({'success': False, 'message': 'No items found in this order!'})
        
        # Add each item to cart
        items_added = 0
        for item in items:
            # Check if item already exists in cart
            existing_item = db.carts.find_one({
                'user_email': current_user.email,
                'name': item.get('name')
            })
            
            if existing_item:
                # Update quantity
                db.carts.update_one(
                    {'_id': existing_item['_id']},
                    {'$inc': {'quantity': item.get('quantity', 1)}}
                )
            else:
                # Add new item to cart
                cart_item = {
                    'user_email': current_user.email,
                    'name': item.get('name'),
                    'price': item.get('price'),
                    'quantity': item.get('quantity', 1),
                    'imageUrl': item.get('image', ''),
                    'description': item.get('description', ''),
                    'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                db.carts.insert_one(cart_item)
            
            items_added += 1
        
        if items_added > 0:
            return jsonify({
                'success': True, 
                'message': f'{items_added} items added to cart!',
                'items_added': items_added
            })
        else:
            return jsonify({'success': False, 'message': 'No items could be added to cart.'})
            
    except Exception as e:
        print(f"Error reordering: {e}")
        return jsonify({'success': False, 'message': f'Error reordering: {str(e)}'})

@routes_bp.route('/customer/orders/<order_id>/hide', methods=['POST'])
@login_required
def customer_hide_order(order_id):
    """Hide order from customer's view (soft delete from customer perspective)."""
    try:
        from bson import ObjectId
        from datetime import datetime
        
        # Find the order and verify it belongs to the current user
        order = db.orders.find_one({
            '_id': ObjectId(order_id),
            'customer_email': current_user.email
        })
        
        if not order:
            return jsonify({'success': False, 'message': 'Order not found!'})
        
        # Set customer_hidden flag to true
        result = db.orders.update_one(
            {'_id': ObjectId(order_id)},
            {
                '$set': {
                    'customer_hidden': True,
                    'hidden_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
        )
        
        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Order removed from your history!'})
        else:
            return jsonify({'success': False, 'message': 'Failed to remove order.'})
            
    except Exception as e:
        print(f"Error hiding order: {e}")
        return jsonify({'success': False, 'message': f'Error removing order: {str(e)}'})

@routes_bp.route('/customer/orders/clear-history', methods=['POST'])
@login_required
def customer_clear_history():
    """Clear all order history for customer (hide all orders from customer view)."""
    try:
        from datetime import datetime
        
        # Update all customer orders to be hidden
        result = db.orders.update_many(
            {'customer_email': current_user.email},
            {
                '$set': {
                    'customer_hidden': True,
                    'history_cleared_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
        )
        
        if result.modified_count > 0:
            print(f"✅ Cleared order history for customer {current_user.email} - {result.modified_count} orders hidden")
            return jsonify({
                'success': True, 
                'message': f'Order history cleared! {result.modified_count} orders removed from view.',
                'orders_hidden': result.modified_count
            })
        else:
            return jsonify({'success': False, 'message': 'No orders found to clear.'})
            
    except Exception as e:
        print(f"Error clearing order history: {e}")
        return jsonify({'success': False, 'message': f'Error clearing order history: {str(e)}'})

@routes_bp.route('/refresh-loyalty-points')
@login_required
def refresh_loyalty_points():
    """Refresh loyalty points for the current user."""
    try:
        new_points = calculate_loyalty_points(current_user.email)
        flash(f'Loyalty points refreshed! You now have {new_points} points.', 'success')
        return redirect(url_for('routes.customer_dashboard'))
    except Exception as e:
        flash('Error refreshing loyalty points.', 'error')
        return redirect(url_for('routes.customer_dashboard'))
