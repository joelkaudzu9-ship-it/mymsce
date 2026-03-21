# app.py
import sys
import os
print("=" * 60)
print("Starting app.py...")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Files in current dir: {os.listdir('.')}")
print("=" * 60)

# Check if .env file exists (though on Render you use environment variables)
if os.path.exists('.env'):
    print("✅ .env file found")
else:
    print("⚠️ .env file not found (this is normal on Render)")

print("\nAttempting imports...")
try:
    print("Importing flask...")
    from flask import Flask
    print("✅ Flask imported")
except Exception as e:
    print(f"❌ Failed to import Flask: {e}")
    sys.exit(1)

try:
    print("Importing models...")
    from models import db, User, Subject, Lesson, Payment, EmailVerification, PasswordReset, Progress
    print("✅ Models imported")
except Exception as e:
    print(f"❌ Failed to import models: {e}")
    sys.exit(1)

try:
    print("Importing forms...")
    from forms import LoginForm, RegistrationForm, PaymentForm, RequestResetForm, ResetPasswordForm
    print("✅ Forms imported")
except Exception as e:
    print(f"❌ Failed to import forms: {e}")
    sys.exit(1)

try:
    print("Importing email_utils...")
    from email_utils import mail, send_verification_email, send_welcome_email, send_password_reset_email, send_payment_confirmation_email, test_smtp_connection
    print("✅ Email utils imported")
except Exception as e:
    print(f"❌ Failed to import email_utils: {e}")
    sys.exit(1)

try:
    print("Importing paychangu...")
    from paychangu import PayChangu
    print("✅ PayChangu imported")
except Exception as e:
    print(f"❌ Failed to import paychangu: {e}")
    sys.exit(1)

print("\n✅ All imports successful!")
print("=" * 60)
import secrets
import json
import re
import requests
import hmac
from werkzeug.utils import secure_filename

import hashlib
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session, send_file, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

from models import db, User, Subject, Lesson, Payment, EmailVerification, PasswordReset, Progress
from forms import LoginForm, RegistrationForm, PaymentForm, RequestResetForm, ResetPasswordForm
from email_utils import mail, send_verification_email, send_welcome_email, send_password_reset_email, \
    send_payment_confirmation_email, test_smtp_connection
from paychangu import PayChangu

# Import test settings
try:
    from test_settings import TEST_MODE, TEST_PRICES
except ImportError:
    TEST_MODE = False
    TEST_PRICES = {}

def flash_message(message, category='info'):
    """Flash a message that will appear as a toast notification"""
    flash(message, category)




load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# File upload configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'uploads'))
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
app.config['ALLOWED_EXTENSIONS'] = {
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv',  # Video
    'mp3', 'wav', 'ogg', 'm4a',                 # Audio
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt',  # Documents
    'jpg', 'jpeg', 'png', 'gif'                  # Images
}

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Session configuration
app.config['SESSION_COOKIE_DOMAIN'] = None
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Database configuration
database_url = os.getenv('DATABASE_URL', 'sqlite:///mymsce.db')

# Fix for Render's PostgreSQL (postgres:// -> postgresql://)
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Only add SSL and connection pool settings for PostgreSQL
if 'postgresql' in database_url:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 5,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'max_overflow': 5,
        'connect_args': {
            'sslmode': 'require',
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5
        }
    }
else:
    # For SQLite, use simple options
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 1,
        'pool_recycle': 300,
        'pool_pre_ping': True
    }




# Email config
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'myMSCE <noreply@mymsce.com>')
app.config['MAIL_MAX_EMAILS'] = None
app.config['MAIL_ASCII_ATTACHMENTS'] = False

# PayChangu config
app.config['PAYCHANGU_PUBLIC_KEY'] = os.getenv('PAYCHANGU_PUBLIC_KEY')
app.config['PAYCHANGU_SECRET_KEY'] = os.getenv('PAYCHANGU_SECRET_KEY')
app.config['PAYCHANGU_WEBHOOK_SECRET'] = os.getenv('PAYCHANGU_WEBHOOK_SECRET')
app.config['PAYCHANGU_MODE'] = os.getenv('PAYCHANGU_MODE', 'sandbox')

# ✅ IMPORTANT - Site URL for emails and webhooks
app.config['SITE_URL'] = os.getenv('SITE_URL', 'https://mymsce.onrender.com').rstrip('/')


# Initialize extensions
db.init_app(app)
mail.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@app.context_processor
def inject_site_url():
    """Make SITE_URL available in all templates"""
    return dict(site_url=app.config['SITE_URL'])



@app.after_request
def add_no_cache_headers(response):
    """Prevent caching of all pages"""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/test-email-debug')
@login_required
def test_email_debug():
    if not current_user.is_admin:
        return "Admin only", 403

    from email_utils import test_smtp_connection
    success, message = test_smtp_connection()

    return f"""
    <h1>Email Test Result</h1>
    <p>Success: {success}</p>
    <p>Message: {message}</p>
    <p>Config:</p>
    <ul>
        <li>MAIL_SERVER: {app.config.get('MAIL_SERVER')}</li>
        <li>MAIL_PORT: {app.config.get('MAIL_PORT')}</li>
        <li>MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}</li>
        <li>MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}</li>
        <li>MAIL_PASSWORD: {'*' * 8 if app.config.get('MAIL_PASSWORD') else 'NOT SET'}</li>
        <li>SITE_URL: {app.config.get('SITE_URL')}</li>
    </ul>
    """



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Create tables and default data
with app.app_context():
    db.create_all()

    # Create admin if not exists
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@mymsce.com')
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        admin = User(
            username='admin',
            email=admin_email,
            is_admin=True,
            is_verified=True,
            email_verified=True
        )
        admin.set_password(os.getenv('ADMIN_PASSWORD', 'admin123'))
        db.session.add(admin)
        db.session.commit()

        # Create sample subjects
        subjects = [
            Subject(name='Mathematics', form=3, description='Form 3 Mathematics', icon='calculator'),
            Subject(name='Physics', form=3, description='Form 3 Physics', icon='flask'),
            Subject(name='Chemistry', form=3, description='Form 3 Chemistry', icon='beaker'),
            Subject(name='Mathematics', form=4, description='Form 4 Mathematics', icon='calculator'),
            Subject(name='Physics', form=4, description='Form 4 Physics', icon='flask'),
            Subject(name='Chemistry', form=4, description='Form 4 Chemistry', icon='beaker'),
            Subject(name='Biology', form=4, description='Form 4 Biology', icon='leaf'),
        ]
        for subject in subjects:
            db.session.add(subject)
        db.session.commit()


# Helper function for YouTube ID extraction
def extract_youtube_id(url):
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)',
        r'youtube\.com\/embed\/([^&\n?#]+)',
        r'^([a-zA-Z0-9_-]{11})$'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user exists
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            flash('Email already registered. Please login.', 'danger')
            return redirect(url_for('login'))

        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            phone=form.phone.data,
            email_verified=False
        )
        user.set_password(form.password.data)

        try:
            db.session.add(user)
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Database error during registration: {str(e)}")
            flash('Registration failed. Please try again.', 'danger')
            return redirect(url_for('register'))

        # Send verification email in background with app context
        def send_verification_with_context():
            with app.app_context():
                try:
                    send_verification_email(user)
                    app.logger.info(f"Verification email sent to {user.email}")
                except Exception as e:
                    app.logger.error(f"Email sending failed for {user.email}: {str(e)}")

        import threading
        email_thread = threading.Thread(target=send_verification_with_context)
        email_thread.daemon = True
        email_thread.start()

        flash('Registration successful! Please check your email to verify your account.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/test-email-send')
def test_email_send():
    """Test email sending - remove after testing"""
    try:
        from flask_mail import Message
        msg = Message(
            subject="Test Email from myMSCE",
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=["your-test-email@gmail.com"],  # Change this
            body="This is a test email from your myMSCE application."
        )
        mail.send(msg)
        return "Email sent successfully! Check your inbox."
    except Exception as e:
        return f"Email failed: {str(e)}"


@app.route('/verify-email/<token>')
def verify_email(token):
    from email_utils import confirm_token

    email = confirm_token(token)
    if not email:
        flash('The verification link is invalid or has expired.', 'danger')
        return redirect(url_for('login'))

    user = User.query.filter_by(email=email).first()
    if user and not user.email_verified:
        user.email_verified = True
        user.is_verified = True
        db.session.commit()

        send_welcome_email(user)
        flash('Your email has been verified! You can now login.', 'success')
    else:
        flash('Email already verified or invalid.', 'info')

    return redirect(url_for('login'))



@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and user.check_password(form.password.data):
            if not user.email_verified:
                flash('Please verify your email before logging in.', 'warning')
                return redirect(url_for('login'))

            login_user(user, remember=form.remember.data)
            app.logger.info(f"User {user.username} (admin: {user.is_admin}) logged in")

            if user.is_admin:
                flash(f'Welcome back Admin {user.username}!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash(f'Welcome back {user.username}!', 'success')
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html', form=form)

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    username = current_user.username
    was_admin = current_user.is_admin

    print(f"🔓 Logging out user: {username} (admin: {was_admin})")

    # ✅ Store flash message BEFORE clearing session
    flash('You have been successfully logged out.', 'success')

    # Logout user
    logout_user()

    # Clear session (flash survives because Flask saves it)
    session.clear()
    session.permanent = False

    # Create response
    response = redirect(url_for('index'))
    response.delete_cookie('session')

    # Add cache control
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    print(f"✅ Logout complete for {username}")

    return response


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = secrets.token_urlsafe(32)
            reset = PasswordReset(
                user_id=user.id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            db.session.add(reset)
            db.session.commit()
            send_password_reset_email(user, token)

        flash('If an account exists with that email, you will receive password reset instructions.', 'info')
        return redirect(url_for('login'))

    return render_template('forgot_password.html', form=form)


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset = PasswordReset.query.filter_by(token=token, used=False).first()
    if not reset or reset.expires_at < datetime.utcnow():
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.get(reset.user_id)
        user.set_password(form.password.data)
        reset.used = True
        db.session.commit()
        flash('Your password has been reset! You can now login.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', form=form)


@app.route('/dashboard')
@login_required
def dashboard():
    # Add cache control headers
    from flask import make_response

    # FORCE REFRESH user from database (not session)
    user = User.query.get(current_user.id)

    # DEBUG - Check what's happening
    print("\n" + "=" * 50)
    print(f"🔍 DASHBOARD ACCESS: {user.username}")
    print(f"Session user ID: {current_user.id}")
    print(f"Database user ID: {user.id}")
    print(f"is_active_subscriber (from DB): {user.is_active_subscriber}")
    print(f"subscription_form: {user.subscription_form}")
    print(f"subscription_type: {user.subscription_type}")
    print(f"subscription_expiry: {user.subscription_expiry}")
    print(f"Days left: {user.get_subscription_days_left()}")
    print("=" * 50 + "\n")

    # If admin, redirect to admin dashboard
    if user.is_admin:
        return redirect(url_for('admin_dashboard'))

    # Check email verification
    if not user.email_verified:
        return redirect(url_for('verify_email_reminder'))

    # Get subjects
    subjects_form3 = Subject.query.filter_by(form=3).order_by(Subject.order).all()
    subjects_form4 = Subject.query.filter_by(form=4).order_by(Subject.order).all()

    # Add lesson counts
    for subject in subjects_form3:
        subject.lesson_count = Lesson.query.filter_by(subject_id=subject.id).count()
    for subject in subjects_form4:
        subject.lesson_count = Lesson.query.filter_by(subject_id=subject.id).count()

    total_lessons = Lesson.query.count()

    # Get user's progress
    from models import Progress

    recent_progress = Progress.query.filter_by(
        user_id=user.id
    ).order_by(Progress.last_watched.desc()).limit(5).all()

    recent_lessons = []
    for prog in recent_progress:
        lesson = Lesson.query.get(prog.lesson_id)
        if lesson:
            if lesson.duration and lesson.duration > 0:
                total_seconds = lesson.duration * 60
                watch_time = min(prog.watch_time, total_seconds)
                progress_percent = min(100, int((watch_time / total_seconds) * 100))
            else:
                progress_percent = 50 if prog.watch_time > 0 else 0

            lesson.progress = progress_percent
            lesson.watch_time = prog.watch_time
            lesson.completed = prog.completed
            lesson.last_watched = prog.last_watched
            recent_lessons.append(lesson)

    completed_lessons = Progress.query.filter_by(
        user_id=user.id,
        completed=True
    ).count()

    sample_lessons = Lesson.query.filter_by(is_free=True).order_by(Lesson.created_at.desc()).limit(3).all()

    # Get user's subscription info
    subscription_info = {
        'is_active': user.is_active_subscriber,
        'form': user.subscription_form if user.is_active_subscriber else None,
        'type': user.subscription_type if user.is_active_subscriber else None,
        'days_left': user.get_subscription_days_left() if user.is_active_subscriber else 0,
        'expiry': user.subscription_expiry.strftime(
            '%d %B %Y') if user.is_active_subscriber and user.subscription_expiry else None
    }

    # Print subscription info for debugging
    print(f"📊 Subscription info sent to template: {subscription_info}")

    # Get recently accessed lessons
    recently_accessed = recent_lessons[:3]

    # Get recommended lessons
    recommended_lessons = []
    if user.is_active_subscriber and user.subscription_form:
        if user.subscription_form == 'form3':
            form = 3
        elif user.subscription_form == 'form4':
            form = 4
        else:
            form = None

        if form:
            started_lesson_ids = [p.lesson_id for p in Progress.query.filter_by(user_id=user.id).all()]
            query = Lesson.query.join(Subject).filter(Subject.form == form)
            if started_lesson_ids:
                query = query.filter(~Lesson.id.in_(started_lesson_ids))
            recommended_lessons = query.order_by(Lesson.created_at.desc()).limit(3).all()

    total_watch_time = db.session.query(db.func.sum(Progress.watch_time)).filter_by(
        user_id=user.id
    ).scalar() or 0
    total_hours_watched = round(total_watch_time / 3600, 1)

    app.logger.info(f"User {user.username} accessed dashboard")

    # Render template with cache control headers
    response = make_response(render_template('dashboard.html',
                                             user=user,
                                             subscription_info=subscription_info,
                                             subjects_form3=subjects_form3,
                                             subjects_form4=subjects_form4,
                                             total_lessons=total_lessons,
                                             completed_lescompleted_lessons=completed_lessons,
                                             total_hours_watched=total_hours_watched,
                                             sample_lessons=sample_lessons,
                                             recent_lessons=recent_lessons,
                                             recently_accessed=recently_accessed,
                                             recommended_lessons=recommended_lessons,
                                             now=datetime.utcnow()))

    # Add cache control headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response
@app.route('/subject/<int:subject_id>')
@login_required
def view_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)

    # ✅ ADMINS CAN ACCESS EVERYTHING
    if current_user.is_admin:
        lessons = Lesson.query.filter_by(subject_id=subject_id).order_by(Lesson.order).all()
        return render_template('subject.html', subject=subject, lessons=lessons)

    # Check access for regular users
    if not current_user.has_access(subject.form):
        flash(f'Please subscribe to access Form {subject.form} lessons.', 'warning')
        return redirect(url_for('pricing'))

    lessons = Lesson.query.filter_by(subject_id=subject_id).order_by(Lesson.order).all()
    return render_template('subject.html', subject=subject, lessons=lessons)


@app.route('/lesson/<int:lesson_id>')
@login_required
def view_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)

    # ✅ ADMINS CAN ACCESS EVERY LESSON
    if current_user.is_admin:
        subject_lessons = Lesson.query.filter_by(
            subject_id=lesson.subject_id
        ).order_by(Lesson.order).all()

        # Get next and previous lessons
        prev_lesson = None
        next_lesson = None
        for i, l in enumerate(subject_lessons):
            if l.id == lesson.id:
                if i > 0:
                    prev_lesson = subject_lessons[i - 1]
                if i < len(subject_lessons) - 1:
                    next_lesson = subject_lessons[i + 1]
                break

        return render_template('lesson.html',
                               lesson=lesson,
                               prev_lesson=prev_lesson,
                               next_lesson=next_lesson,
                               subject_lessons=subject_lessons)

    # Check access for regular users
    if not current_user.has_access(lesson.form) and not lesson.is_free:
        flash('Please subscribe to access this lesson.', 'warning')
        return redirect(url_for('pricing'))

    # ✅ Get or create progress record for this user and lesson
    from models import Progress
    from datetime import datetime

    progress = Progress.query.filter_by(
        user_id=current_user.id,
        lesson_id=lesson.id
    ).first()

    # If no progress record exists, create one
    if not progress:
        progress = Progress(
            user_id=current_user.id,
            lesson_id=lesson.id,
            watch_time=0,
            completed=False,
            last_watched=datetime.utcnow()
        )
        db.session.add(progress)
        db.session.commit()
    else:
        # Update last_watched timestamp
        progress.last_watched = datetime.utcnow()
        db.session.commit()

    # Calculate current progress percentage for display
    if lesson.duration and lesson.duration > 0:
        total_seconds = lesson.duration * 60
        current_progress = min(100, int((progress.watch_time / total_seconds) * 100))
    else:
        current_progress = 0

    # Get all lessons in same subject with their progress
    subject_lessons = Lesson.query.filter_by(
        subject_id=lesson.subject_id
    ).order_by(Lesson.order).all()

    # Enhance subject lessons with progress data
    for l in subject_lessons:
        # Get progress for each lesson
        l_progress = Progress.query.filter_by(
            user_id=current_user.id,
            lesson_id=l.id
        ).first()

        if l_progress:
            if l.duration and l.duration > 0:
                total_seconds = l.duration * 60
                l.user_progress = min(100, int((l_progress.watch_time / total_seconds) * 100))
                l.user_watch_time = l_progress.watch_time
                l.user_completed = l_progress.completed
            else:
                l.user_progress = 50 if l_progress.watch_time > 0 else 0
                l.user_watch_time = l_progress.watch_time
                l.user_completed = l_progress.completed
        else:
            l.user_progress = 0
            l.user_watch_time = 0
            l.user_completed = False

    # Get next and previous lessons with their progress
    prev_lesson = None
    next_lesson = None
    for i, l in enumerate(subject_lessons):
        if l.id == lesson.id:
            if i > 0:
                prev_lesson = subject_lessons[i - 1]
            if i < len(subject_lessons) - 1:
                next_lesson = subject_lessons[i + 1]
            break

    return render_template('lesson.html',
                           lesson=lesson,
                           prev_lesson=prev_lesson,
                           next_lesson=next_lesson,
                           subject_lessons=subject_lessons,
                           user_progress=current_progress,
                           watch_time=progress.watch_time if progress else 0,
                           completed=progress.completed if progress else False,
                           last_watched=progress.last_watched if progress else None)







@app.route('/search')
@login_required
def search():
    """Dedicated search results page"""
    query = request.args.get('q', '').strip()

    if len(query) < 2:
        flash('Please enter at least 2 characters to search', 'info')
        return redirect(url_for('dashboard'))

    # Search in subjects
    subjects = Subject.query.filter(
        Subject.name.ilike(f'%{query}%')
    ).order_by(Subject.form, Subject.order).all()

    # Search in lessons
    lessons = Lesson.query.filter(
        Lesson.title.ilike(f'%{query}%')
    ).order_by(Lesson.created_at.desc()).all()

    # Calculate total results
    total_results = len(subjects) + len(lessons)

    # Get lesson counts for subjects
    for subject in subjects:
        subject.lesson_count = Lesson.query.filter_by(subject_id=subject.id).count()

    return render_template('search_results.html',
                           query=query,
                           subjects=subjects,
                           lessons=lessons,
                           total_results=total_results)

@app.route('/api/lesson/<int:lesson_id>/complete', methods=['POST'])
@login_required
def api_lesson_complete(lesson_id):
    """Mark lesson as complete"""
    lesson = Lesson.query.get_or_404(lesson_id)

    # TODO: Save to Progress model when implemented
    app.logger.info(f"User {current_user.id} completed lesson {lesson_id}")

    return jsonify({
        'success': True,
        'message': 'Lesson marked as complete'
    })


@app.route('/pricing')
def pricing():
    return render_template('pricing.html')


@app.route('/subscribe/<form_type>/<duration>')
@login_required
def subscribe(form_type, duration):
    if not current_user.email_verified:
        flash('Please verify your email before subscribing.', 'warning')
        return redirect(url_for('verify_email_reminder'))

    # Real prices
    real_prices = {
        'form3': {'daily': 1030, 'weekly': 6695, 'monthly': 12500},
        'form4': {'daily': 1030, 'weekly': 6695, 'monthly': 12500},
        'combined': {'daily': 1545, 'weekly': 8500, 'monthly': 19500}
    }

    # ✅ CHECK FOR EXISTING ACTIVE SUBSCRIPTION
    # BUT skip if this is a confirmed upgrade
    if not session.get('confirmed_upgrade', False) and current_user.is_active_subscriber:
        # Check if it's not expired
        if current_user.subscription_expiry and current_user.subscription_expiry > datetime.utcnow():
            # User already has active subscription
            days_left = current_user.get_subscription_days_left()

            # Store subscription info in session for the confirmation page
            session['pending_subscription'] = {
                'form_type': form_type,
                'duration': duration,
                'amount': real_prices[form_type][duration]
            }

            # Redirect to confirmation page
            return redirect(url_for('confirm_subscription_upgrade'))

    # ✅ Clear the confirmed_upgrade flag after using it
    if session.get('confirmed_upgrade'):
        session.pop('confirmed_upgrade', None)

    # Use test prices if in TEST_MODE
    if TEST_MODE:
        prices = TEST_PRICES
        flash(
            f'🔧 TEST MODE: You\'re paying {TEST_PRICES[form_type][duration]} MWK instead of {real_prices[form_type][duration]} MWK',
            'info')
    else:
        prices = real_prices

    if form_type not in prices or duration not in prices[form_type]:
        flash('Invalid subscription type.', 'danger')
        return redirect(url_for('pricing'))

    amount = prices[form_type][duration]

    # Generate unique reference
    reference = f"SUB-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{current_user.id}"
    if TEST_MODE:
        reference = f"TEST-{reference}"

    payment = Payment(
        user_id=current_user.id,
        amount=amount,
        subscription_type=duration,
        subscription_form=form_type,
        reference=reference,
        status='pending'
    )
    db.session.add(payment)
    db.session.commit()

    return render_template('payment.html',
                           form_type=form_type,
                           duration=duration,
                           amount=amount,
                           reference=reference,
                           payment_id=payment.id,
                           test_mode=TEST_MODE)


@app.route('/confirm-subscription-upgrade')
@login_required
def confirm_subscription_upgrade():
    """Show confirmation page for upgrading subscription"""
    pending = session.get('pending_subscription')

    if not pending:
        flash('No pending subscription found.', 'warning')
        return redirect(url_for('pricing'))

    # Format current plan name
    current_plan = f"{current_user.subscription_form.upper()} - {current_user.subscription_type.title()}"

    # Format new plan name
    new_plan = f"{pending['form_type'].upper()} - {pending['duration'].title()}"

    days_left = current_user.get_subscription_days_left()

    return render_template('confirm_subscription.html',
                           current_plan=current_plan,
                           new_plan=new_plan,
                           days_left=days_left)


@app.route('/process-upgrade', methods=['GET'])
@login_required
def process_upgrade():
    """Process the confirmed upgrade"""
    pending = session.get('pending_subscription')

    if not pending:
        flash('No pending subscription found.', 'warning')
        return redirect(url_for('pricing'))

    # ✅ Set a flag in session that this is a confirmed upgrade
    session['confirmed_upgrade'] = True

    # Redirect to the normal subscribe flow
    return redirect(url_for('subscribe',
                            form_type=pending['form_type'],
                            duration=pending['duration']))


@app.route('/process-payment/<int:payment_id>', methods=['POST'])
@login_required
def process_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)

    if payment.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard'))

    phone = request.form.get('phone_number', '').strip()
    method = request.form.get('payment_method')

    if not phone or not method:
        flash('Please provide phone number and payment method', 'danger')
        return redirect(url_for('subscribe', form_type=payment.subscription_form, duration=payment.subscription_type))

    # Clean phone number
    phone = re.sub(r'\D', '', phone)

    if phone.startswith('265'):
        phone = '0' + phone[3:]
    elif not phone.startswith('0'):
        phone = '0' + phone[-9:] if len(phone) >= 9 else phone

    if len(phone) > 10:
        phone = phone[:10]
    elif len(phone) == 9:
        phone = '0' + phone

    payment.phone_number = phone
    payment.payment_method = method
    db.session.commit()

    paychangu = PayChangu(mode=app.config['PAYCHANGU_MODE'])
    app.logger.info(f"Processing payment: {payment.id}, Amount: {payment.amount}, Phone: {phone}, Method: {method}")

    try:
        result = paychangu.initiate_mobile_money_payment(
            amount=payment.amount,
            phone_number=phone,
            email=current_user.email,
            name=current_user.username,
            reference=payment.reference,
            callback_url="https://lusty-velda-wavy.ngrok-free.dev/paychangu-webhook"

        )

        app.logger.info(f"PayChangu response: {result}")

        if result and isinstance(result, dict):
            if result.get('status') == 'success' and 'data' in result:
                payment.charge_id = result['data'].get('charge_id')
                payment.paychangu_response = json.dumps(result)
                db.session.commit()
                flash('Payment initiated. Please check your phone to complete the payment.', 'info')
                return redirect(url_for('payment_status', payment_id=payment.id))
            else:
                error_message = result.get('message', 'Unknown error occurred')
                app.logger.error(f"Payment initiation failed: {error_message}")
                flash(f'Payment failed: {error_message}', 'danger')
        else:
            app.logger.error(f"Unexpected response format: {result}")
            flash('Payment service returned an unexpected response. Please try again.', 'danger')

    except Exception as e:
        app.logger.error(f"Exception during payment processing: {str(e)}", exc_info=True)
        flash(f'Payment error: {str(e)}', 'danger')

    return redirect(url_for('pricing'))


@app.route('/payment-status/<int:payment_id>')
def payment_status(payment_id):  # REMOVED @login_required!
    payment = Payment.query.get_or_404(payment_id)

    # If user is logged in and owns the payment, show full details
    if current_user.is_authenticated and payment.user_id == current_user.id:
        return render_template('payment_status.html', payment=payment)

    # Otherwise show limited public version
    return render_template('payment_status_public.html',
                           reference=payment.reference,
                           amount=payment.amount,
                           status=payment.status)

@app.route('/paychangu-webhook', methods=['POST'])
@app.route('/paychangu-webhook/', methods=['POST'])
@app.route('/paychange-webhook', methods=['POST'])
@app.route('/paychange-webhook/', methods=['POST'])
def paychangu_webhook():
    """PayChangu Webhook Handler - Accepts sandbox webhooks without signature"""
    try:
        import hmac
        import hashlib
        import json
        import time
        from datetime import datetime, timedelta

        print("\n" + "🔔" * 50)
        print("WEBHOOK RECEIVED")
        print(f"Request method: {request.method}")
        print(f"Request headers: {dict(request.headers)}")

        payload = request.get_data()
        print(f"Raw payload length: {len(payload)} bytes")
        print(f"Raw payload preview: {payload[:200]}...")

        signature = request.headers.get('Signature')
        print(f"Signature header: {signature}")

        # FOR SANDBOX: Accept webhooks even without signature
        if app.config.get('PAYCHANGU_MODE') == 'sandbox' and not signature:
            print("⚠️ Sandbox mode: Accepting webhook without signature")
            try:
                data = request.json
                print(f"Parsed JSON data: {json.dumps(data, indent=2)}")
            except Exception as e:
                print(f"❌ Failed to parse JSON: {e}")
                data = {}

            # Process payment
            process_webhook_payment(data)
            return jsonify({'status': 'activated (sandbox)'}), 200

        # For live mode, require signature verification
        if not signature:
            print("❌ No signature header - rejecting")
            return jsonify({'error': 'No signature'}), 401

        # VERIFY SIGNATURE for live mode
        secret = app.config.get('PAYCHANGU_WEBHOOK_SECRET')
        if not secret:
            print("❌ Webhook secret not configured")
            return jsonify({'error': 'Server configuration error'}), 500

        expected = hmac.new(
            key=secret.encode('utf-8'),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            print("❌ Invalid signature - rejecting webhook")
            return jsonify({'error': 'Invalid signature'}), 401

        print("✅ Signature verified")

        # Parse data
        try:
            data = request.json
            print(f"Parsed JSON data: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"❌ Failed to parse JSON: {e}")
            data = {}

        # Process the webhook for live mode
        process_webhook_payment(data)

        return jsonify({'status': 'received'}), 200

    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400


def process_webhook_payment(data):
    """Helper function to process payment from webhook data"""
    from datetime import datetime, timedelta
    import time
    import json

    print("\n📦 PROCESSING WEBHOOK PAYMENT")
    print(f"Raw data type: {type(data)}")
    print(f"Raw data: {data}")

    # Check if data is None or empty
    if not data:
        print("❌ No data received")
        return

    # Check if data is a dictionary
    if not isinstance(data, dict):
        print(f"❌ Data is not a dictionary: {type(data)}")
        return

    # Get references from webhook - try multiple possible locations
    webhook_reference = data.get('reference') or data.get('data', {}).get('reference')
    charge_id = data.get('charge_id') or data.get('data', {}).get('charge_id')
    tx_ref = data.get('tx_ref') or data.get('data', {}).get('tx_ref')
    ref_id = data.get('ref_id') or data.get('data', {}).get('ref_id')

    print(f"🔍 Looking for payment with:")
    print(f"   - reference: {webhook_reference}")
    print(f"   - charge_id: {charge_id}")
    print(f"   - tx_ref: {tx_ref}")
    print(f"   - ref_id: {ref_id}")

    payment = None

    # Method 1: Try to find payment by our reference
    if webhook_reference and not payment:
        payment = Payment.query.filter_by(reference=webhook_reference).first()
        if payment:
            print(f"✅ Found payment by reference: {webhook_reference}")

    # Method 2: Try by charge_id (THIS SHOULD WORK!)
    if charge_id and not payment:
        payment = Payment.query.filter_by(charge_id=charge_id).first()
        if payment:
            print(f"✅ Found payment by charge_id: {charge_id}")

    # Method 3: Try by tx_ref (transaction reference)
    if tx_ref and not payment:
        payment = Payment.query.filter_by(transaction_id=tx_ref).first()
        if payment:
            print(f"✅ Found payment by tx_ref: {tx_ref}")

    # Method 4: More aggressive JSON search
    if not payment:
        print("🔍 AGGRESSIVE SEARCH in paychangu_response...")
        all_payments = Payment.query.filter_by(status='pending').all()
        print(f"Found {len(all_payments)} pending payments to search")

        for p in all_payments:
            if p.paychangu_response:
                try:
                    response_data = json.loads(p.paychangu_response)

                    # Check if this payment's charge_id matches ANYWHERE
                    if charge_id and charge_id == response_data.get('data', {}).get('charge_id'):
                        payment = p
                        print(f"✅ Found payment {p.id} by charge_id in response")
                        break

                    # Check if webhook reference appears in response
                    if webhook_reference and webhook_reference in p.paychangu_response:
                        payment = p
                        print(f"✅ Found payment {p.id} by reference string")
                        break

                    # Check if the ref_id matches
                    if ref_id and ref_id == response_data.get('data', {}).get('ref_id'):
                        payment = p
                        print(f"✅ Found payment {p.id} by ref_id")
                        break

                    # Also check if charge_id exists anywhere in the raw string
                    if charge_id and charge_id in p.paychangu_response:
                        payment = p
                        print(f"✅ Found payment {p.id} by charge_id string match")
                        break

                except Exception as e:
                    print(f"⚠️ Error parsing JSON for payment {p.id}: {e}")
                    continue

    # If still not found, try direct charge_id match (THIS SHOULD WORK!)
    if not payment and charge_id:
        print(f"🔍 Direct charge_id search: {charge_id}")
        payment = Payment.query.filter_by(charge_id=charge_id).first()
        if payment:
            print(f"✅ Found payment by direct charge_id: {payment.id}")

    # RETRY LOGIC: If payment not found, wait and retry MULTIPLE times
    if not payment:
        print("⏳ Payment not found - will retry up to 3 times with delays...")

        for attempt in range(1, 4):
            print(f"⏳ Retry attempt {attempt}/3...")
            time.sleep(2)  # Wait 2 seconds

            # Clear session cache and get fresh session
            db.session.remove()

            # Try direct charge_id search again
            if charge_id:
                payment = Payment.query.filter_by(charge_id=charge_id).first()
                if payment:
                    print(f"✅ Found payment on retry attempt {attempt}: {payment.id}")
                    break

            # Also try reference search again
            if not payment and webhook_reference:
                payment = Payment.query.filter_by(reference=webhook_reference).first()
                if payment:
                    print(f"✅ Found payment by reference on retry attempt {attempt}: {payment.id}")
                    break

            # Also try tx_ref search
            if not payment and tx_ref:
                payment = Payment.query.filter_by(transaction_id=tx_ref).first()
                if payment:
                    print(f"✅ Found payment by tx_ref on retry attempt {attempt}: {payment.id}")
                    break

        if not payment:
            print("❌ Payment still not found after 3 retries")

    if payment:
        print(f"✅ Found payment ID: {payment.id}, User: {payment.user_id}")

        if payment.status == 'pending':
            print("✅ Payment is pending - activating now...")

            # Get user
            user = User.query.get(payment.user_id)
            if not user:
                print(f"❌ User not found for payment {payment.id}")
                return

            # ✅ CRITICAL - Set ALL subscription fields
            user.is_active_subscriber = True
            user.subscription_form = payment.subscription_form    # ← This was missing!
            user.subscription_type = payment.subscription_type    # ← This was missing!

            # Calculate days based on subscription type
            days = {'daily': 1, 'weekly': 7, 'monthly': 30}.get(payment.subscription_type, 1)

            # Update expiry
            if user.subscription_expiry and user.subscription_expiry > datetime.utcnow():
                user.subscription_expiry += timedelta(days=days)
                print(f"📅 Extended existing subscription by {days} days")
            else:
                user.subscription_expiry = datetime.utcnow() + timedelta(days=days)
                print(f"📅 New subscription for {days} days")

            # Update payment
            payment.status = 'completed'
            payment.completed_at = datetime.utcnow()
            if tx_ref:
                payment.transaction_id = tx_ref

            # Commit all changes
            db.session.commit()

            print(f"✅✅✅ ACTIVATED: {user.username}")
            print(f"📊 Form: {user.subscription_form}, Type: {user.subscription_type}, Expiry: {user.subscription_expiry}")

            # Send email
            try:
                send_payment_confirmation_email(user, payment)
                print(f"📧 Confirmation email sent to {user.email}")
            except Exception as e:
                print(f"⚠️ Email sending failed: {e}")
        else:
            print(f"⚠️ Payment already processed with status: {payment.status}")
    else:
        print(f"❌ NO PAYMENT FOUND for any reference")
        print(f"   - reference: {webhook_reference}")
        print(f"   - charge_id: {charge_id}")
        print(f"   - tx_ref: {tx_ref}")
        print(f"   - ref_id: {ref_id}")





@app.route('/payment-success')
def payment_success():
    flash('Payment successful! You now have access to your lessons.', 'success')
    response = redirect(url_for('dashboard'))

    # Force browser to get fresh data
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response


@app.route('/payment-failed')
def payment_failed():
    flash('Payment failed. Please try again.', 'danger')
    return redirect(url_for('pricing'))


@app.route('/verify-payment/<reference>')
@login_required
def verify_payment(reference):
    """Manually verify payment status with PayChangu API"""
    import requests

    # Find the payment
    payment = Payment.query.filter_by(reference=reference).first()
    if not payment:
        flash('Payment not found', 'danger')
        return redirect(url_for('dashboard'))

    # Only the user who made payment can verify
    if payment.user_id != current_user.id and not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard'))

    # Call PayChangu to verify transaction status
    try:
        # PayChangu transaction verification endpoint
        url = f"https://api.paychangu.com/transactions/verify/{payment.transaction_id or payment.charge_id}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {app.config['PAYCHANGU_SECRET_KEY']}"
        }

        print(f"🔍 Verifying payment with PayChangu: {url}")
        response = requests.get(url, headers=headers, timeout=30)

        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        if response.status_code == 200:
            data = response.json()
            # Check different possible status fields
            tx_status = data.get('status') or data.get('data', {}).get('status')

            if tx_status in ['success', 'successful', 'completed']:
                # Update payment status
                payment.status = 'completed'
                payment.completed_at = datetime.utcnow()

                # Activate subscription
                user = User.query.get(payment.user_id)
                days = payment.get_days_for_subscription()

                user.is_active_subscriber = True
                user.subscription_type = payment.subscription_type
                user.subscription_form = payment.subscription_form

                if user.subscription_expiry and user.subscription_expiry > datetime.utcnow():
                    user.subscription_expiry += timedelta(days=days)
                else:
                    user.subscription_expiry = datetime.utcnow() + timedelta(days=days)

                db.session.commit()
                flash('✅ Payment verified! Your subscription is now active.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash(f'⏳ Payment status: {tx_status or "pending"}', 'warning')
        else:
            # Try alternative endpoint
            alt_url = f"https://api.paychangu.com/verify-payment/{reference}"
            alt_response = requests.get(alt_url, headers=headers, timeout=30)

            if alt_response.status_code == 200:
                alt_data = alt_response.json()
                if alt_data.get('status') == 'success':
                    # Same activation code as above
                    payment.status = 'completed'
                    payment.completed_at = datetime.utcnow()

                    user = User.query.get(payment.user_id)
                    days = payment.get_days_for_subscription()
                    user.is_active_subscriber = True
                    user.subscription_type = payment.subscription_type
                    user.subscription_form = payment.subscription_form

                    if user.subscription_expiry and user.subscription_expiry > datetime.utcnow():
                        user.subscription_expiry += timedelta(days=days)
                    else:
                        user.subscription_expiry = datetime.utcnow() + timedelta(days=days)

                    db.session.commit()
                    flash('✅ Payment verified! Your subscription is now active.', 'success')
                    return redirect(url_for('dashboard'))

            flash('Could not verify payment status at this time. Please try again later.', 'danger')

    except Exception as e:
        print(f"❌ Verification error: {str(e)}")
        flash(f'Error verifying payment: {str(e)}', 'danger')

    return redirect(url_for('payment_status', payment_id=payment.id))


@app.route('/profile')
@login_required
def profile():
    payments = Payment.query.filter_by(user_id=current_user.id).order_by(Payment.created_at.desc()).all()
    return render_template('profile.html', payments=payments)


@app.route('/verify-email-reminder')
@login_required
def verify_email_reminder():
    if current_user.email_verified:
        return redirect(url_for('dashboard'))
    return render_template('verify_email_reminder.html')


@app.route('/resend-verification')
@login_required
def resend_verification():
    """Resend verification email to current user"""
    if current_user.email_verified:
        flash('Your email is already verified.', 'info')
        return redirect(url_for('dashboard'))

    send_verification_email(current_user)
    flash('Verification email sent. Please check your inbox.', 'info')
    return redirect(url_for('verify_email_reminder'))


@app.route('/user-menu')
@login_required
def user_menu():
    """User menu page with all account options"""
    return render_template('user_menu.html', user=current_user)


# Admin Routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        app.logger.warning(f"Non-admin user {current_user.username} attempted to access admin dashboard")
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    app.logger.info(f"Admin {current_user.username} accessing admin dashboard")

    # Get current time for template
    now = datetime.utcnow()

    # User stats
    total_users = User.query.count()
    new_users_today = User.query.filter(
        User.created_at >= datetime.utcnow().date()
    ).count()

    # Subscription stats
    active_subscribers = User.query.filter_by(is_active_subscriber=True).count()

    # Payment stats
    completed_payments = Payment.query.filter_by(status='completed').count()
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(status='completed').scalar() or 0

    # Content stats
    total_subjects = Subject.query.count()
    total_lessons = Lesson.query.count()

    # Recent data
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(10).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    # Subscription breakdown
    form3_count = User.query.filter_by(subscription_form='form3', is_active_subscriber=True).count()
    form4_count = User.query.filter_by(subscription_form='form4', is_active_subscriber=True).count()
    combined_count = User.query.filter_by(subscription_form='combined', is_active_subscriber=True).count()

    # Revenue chart data (last 30 days)
    daily_revenue = []
    dates = []

    for i in range(30):
        day = datetime.utcnow() - timedelta(days=29 - i)
        next_day = day + timedelta(days=1)

        day_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.status == 'completed',
            Payment.completed_at >= day,
            Payment.completed_at < next_day
        ).scalar() or 0

        daily_revenue.append(float(day_revenue))
        dates.append(day.strftime('%d %b'))

    # Get test mode from session or global
    test_mode = session.get('test_mode', TEST_MODE)

    return render_template('admin/dashboard.html',
                           datetime=datetime,
                           total_users=total_users,
                           new_users_today=new_users_today,
                           active_subscribers=active_subscribers,
                           total_revenue=total_revenue,
                           completed_payments=completed_payments,
                           total_subjects=total_subjects,
                           total_lessons=total_lessons,
                           recent_payments=recent_payments,
                           recent_users=recent_users,
                           form3_count=form3_count,
                           form4_count=form4_count,
                           combined_count=combined_count,
                           revenue_labels=dates,
                           revenue_data=daily_revenue,
                           test_mode=test_mode)


@app.route('/watch/<int:lesson_id>')
@login_required
def watch_lesson(lesson_id):
    """Dedicated YouTube player page"""
    lesson = Lesson.query.get_or_404(lesson_id)

    # Check access
    if not current_user.has_access(lesson.form) and not lesson.is_free and not current_user.is_admin:
        flash('Please subscribe to access this lesson.', 'warning')
        return redirect(url_for('pricing'))

    # Extract YouTube ID
    video_id = lesson.video_url
    if 'youtu.be' in video_id:
        video_id = video_id.split('youtu.be/')[1].split('?')[0]
    elif 'v=' in video_id:
        video_id = video_id.split('v=')[1].split('&')[0]
    elif 'embed' in video_id:
        video_id = video_id.split('embed/')[1].split('?')[0]

    return render_template('watch.html',
                           lesson=lesson,
                           video_id=video_id)





@app.route('/admin/user/<int:user_id>/payments')
@login_required
def admin_user_payments(user_id):
    """View payment history for a specific user"""
    user = User.query.get_or_404(user_id)
    payments = Payment.query.filter_by(user_id=user_id).order_by(Payment.created_at.desc()).all()
    return render_template('admin/user_payments.html', user=user, payments=payments)




@app.route('/admin/toggle-test-mode')
@login_required
def toggle_test_mode():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        current_test_mode = session.get('test_mode', False)
        session['test_mode'] = not current_test_mode
        return jsonify({'success': True, 'test_mode': session['test_mode']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/user/<int:user_id>')
@login_required
def admin_user_detail(user_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    payments = Payment.query.filter_by(user_id=user_id).order_by(Payment.created_at.desc()).all()
    return render_template('admin/user_detail.html', user=user, payments=payments)


@app.route('/admin/user/<int:user_id>/reset-password', methods=['POST'])
@login_required
def admin_reset_user_password(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    user = User.query.get_or_404(user_id)

    try:
        token = secrets.token_urlsafe(32)
        reset = PasswordReset(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(reset)
        db.session.commit()

        send_password_reset_email(user, token)
        app.logger.info(f"Admin {current_user.username} reset password for user {user.username}")

        return jsonify({'success': True, 'message': f'Password reset email sent to {user.email}'})
    except Exception as e:
        app.logger.error(f"Error resetting password: {str(e)}")
        return jsonify({'success': False, 'message': f'Error sending reset email: {str(e)}'}), 500


@app.route('/admin/subjects')
@login_required
def admin_subjects():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    subjects = Subject.query.order_by(Subject.form, Subject.order).all()
    return render_template('admin/subjects.html', subjects=subjects)


@app.route('/admin/subject/create', methods=['GET', 'POST'])
@login_required
def admin_create_subject():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        subject = Subject(
            name=request.form.get('name'),
            form=request.form.get('form'),
            description=request.form.get('description'),
            icon=request.form.get('icon', 'book'),
            order=request.form.get('order', 0)
        )
        db.session.add(subject)
        db.session.commit()
        flash('Subject created successfully', 'success')
        return redirect(url_for('admin_subjects'))

    return render_template('admin/create_subject.html')


@app.route('/admin/subject/<int:subject_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_subject(subject_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    subject = Subject.query.get_or_404(subject_id)

    if request.method == 'POST':
        subject.name = request.form.get('name')
        subject.form = request.form.get('form')
        subject.description = request.form.get('description')
        subject.icon = request.form.get('icon', 'book')
        subject.order = request.form.get('order', 0)
        db.session.commit()
        flash('Subject updated successfully', 'success')
        return redirect(url_for('admin_subjects'))

    return render_template('admin/edit_subject.html', subject=subject)


@app.route('/admin/subject/<int:subject_id>/delete')
@login_required
def admin_delete_subject(subject_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    flash('Subject deleted successfully', 'success')
    return redirect(url_for('admin_subjects'))


@app.route('/admin/lessons')
@login_required
def admin_lessons():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    lessons = Lesson.query.order_by(Lesson.created_at.desc()).all()
    return render_template('admin/lessons.html', lessons=lessons)


@app.route('/admin/lesson/create', methods=['GET', 'POST'])
@login_required
def admin_create_lesson():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    subjects = Subject.query.all()

    if request.method == 'POST':
        subject = Subject.query.get(request.form.get('subject_id'))

        # Handle file upload
        file = request.files.get('file')
        file_path = None
        file_name = None
        file_size = 0
        file_extension = None

        if file and file.filename and allowed_file(file.filename):
            # Secure the filename
            filename = secure_filename(file.filename)
            # Add timestamp to avoid duplicates
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            new_filename = f"{timestamp}_{filename}"

            # Save file
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))

            file_path = new_filename
            file_name = filename
            file_size = os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
            file_extension = filename.rsplit('.', 1)[1].lower()

        # Determine content type
        content_type = request.form.get('content_type', 'video')

        lesson = Lesson(
            title=request.form.get('title'),
            description=request.form.get('description'),
            content=request.form.get('content'),
            content_type=content_type,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            file_extension=file_extension,
            video_url=request.form.get('video_url') if content_type == 'youtube' else None,
            video_type='youtube' if content_type == 'youtube' else None,
            subject_id=subject.id,
            form=subject.form,
            order=request.form.get('order', 0),
            is_free=request.form.get('is_free') == 'on',
            downloadable=request.form.get('downloadable') == 'on' if content_type != 'youtube' else False
        )

        db.session.add(lesson)
        db.session.commit()
        flash('Lesson created successfully', 'success')
        return redirect(url_for('admin_lessons'))

    return render_template('admin/create_lesson.html', subjects=subjects)


@app.route('/debug-db')
def debug_db():
    """Check database connection status"""
    try:
        from sqlalchemy import text
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()

        return jsonify({
            'status': 'connected',
            'database_url': app.config['SQLALCHEMY_DATABASE_URI'][:50] + '...',
            'pool_settings': app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {}),
            'test_query': result
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500



@app.route('/admin/lesson/<int:lesson_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_lesson(lesson_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    lesson = Lesson.query.get_or_404(lesson_id)
    subjects = Subject.query.all()

    if request.method == 'POST':
        lesson.title = request.form.get('title')
        lesson.description = request.form.get('description')
        lesson.content = request.form.get('content')
        lesson.video_url = request.form.get('video_url')
        lesson.video_type = request.form.get('video_type', 'youtube')
        lesson.order = request.form.get('order', 0)
        lesson.is_free = request.form.get('is_free') == 'on'

        subject = Subject.query.get(request.form.get('subject_id'))
        lesson.subject_id = subject.id
        lesson.form = subject.form

        db.session.commit()
        flash('Lesson updated successfully', 'success')
        return redirect(url_for('admin_lessons'))

    return render_template('admin/edit_lesson.html', lesson=lesson, subjects=subjects)


@app.route('/admin/lesson/<int:lesson_id>/delete')
@login_required
def admin_delete_lesson(lesson_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    lesson = Lesson.query.get_or_404(lesson_id)
    db.session.delete(lesson)
    db.session.commit()
    flash('Lesson deleted successfully', 'success')
    return redirect(url_for('admin_lessons'))


@app.route('/admin/lesson/<int:lesson_id>/make-sample', methods=['POST'])
@login_required
def make_lesson_sample(lesson_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    lesson = Lesson.query.get_or_404(lesson_id)
    lesson.is_free = True
    db.session.commit()
    return jsonify({'success': True, 'message': 'Lesson is now a free sample'})


@app.route('/admin/lesson/<int:lesson_id>/remove-sample', methods=['POST'])
@login_required
def remove_lesson_sample(lesson_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    lesson = Lesson.query.get_or_404(lesson_id)
    lesson.is_free = False
    db.session.commit()
    return jsonify({'success': True, 'message': 'Sample status removed'})


@app.route('/admin/sample-lessons')
@login_required
def admin_sample_lessons():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    all_lessons = Lesson.query.order_by(Lesson.created_at.desc()).all()
    sample_lessons = [l for l in all_lessons if l.is_free]
    premium_lessons = [l for l in all_lessons if not l.is_free]

    return render_template('admin/sample_lessons.html',
                           sample_lessons=sample_lessons,
                           premium_lessons=premium_lessons,
                           total_lessons=len(all_lessons))


@app.route('/admin/payments')
@login_required
def admin_payments():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    from datetime import datetime
    now = datetime.utcnow()  # Get current time
    payments = Payment.query.order_by(Payment.created_at.desc()).all()

    return render_template('admin/payments.html',
                           payments=payments,
                           now=now)  # Pass the datetime object


@app.route('/admin/activate-payment/<int:payment_id>')
@login_required
def admin_activate_payment(payment_id):
    if not current_user.is_admin:
        return "Admin only", 403

    payment = Payment.query.get_or_404(payment_id)

    payment.status = 'completed'
    payment.completed_at = datetime.utcnow()

    user = User.query.get(payment.user_id)
    days = payment.get_days_for_subscription()

    user.subscription_type = payment.subscription_type
    user.subscription_form = payment.subscription_form
    user.is_active_subscriber = True

    if user.subscription_expiry and user.subscription_expiry > datetime.utcnow():
        user.subscription_expiry += timedelta(days=days)
    else:
        user.subscription_expiry = datetime.utcnow() + timedelta(days=days)

    db.session.commit()
    flash(f'Payment manually activated for user {user.username}', 'success')
    return redirect(url_for('admin_payments'))


# API Routes
@app.route('/api/check-subscription')
@login_required
def check_subscription():
    user = User.query.get(current_user.id)

    if user.is_active_subscriber and user.subscription_expiry < datetime.utcnow():
        user.is_active_subscriber = False
        user.subscription_type = 'none'
        user.subscription_form = 'none'
        db.session.commit()
        return jsonify({'changed': True, 'status': 'expired'})

    return jsonify({'changed': False})


@app.route('/api/payment-status/<int:payment_id>')
@login_required
def api_payment_status(payment_id):
    payment = Payment.query.get_or_404(payment_id)

    if payment.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({
        'status': payment.status,
        'amount': payment.amount,
        'reference': payment.reference
    })

# Debug Routes
@app.route('/debug-paychangu')
@login_required
def debug_paychangu():
    if not current_user.is_admin:
        return "Admin only", 403

    config_info = {
        'mode': app.config.get('PAYCHANGU_MODE'),
        'base_url': 'https://sandbox.paychangu.com' if app.config.get('PAYCHANGU_MODE') == 'sandbox' else 'https://api.paychangu.com',
        'has_public_key': bool(app.config.get('PAYCHANGU_PUBLIC_KEY')),
        'has_secret_key': bool(app.config.get('PAYCHANGU_SECRET_KEY')),
        'public_key': app.config.get('PAYCHANGU_PUBLIC_KEY', '')[:15] + '...',
        'secret_key': app.config.get('PAYCHANGU_SECRET_KEY', '')[:15] + '...',
        'site_url': app.config.get('SITE_URL'),
        'webhook_url': f"{app.config.get('SITE_URL')}/paychangu-webhook"
    }
    return jsonify(config_info)


@app.route('/debug-phone/<phone>')
@login_required
def debug_phone(phone):
    if not current_user.is_admin:
        return "Admin only", 403

    from paychangu import PayChangu

    paychangu = PayChangu(mode=app.config.get('PAYCHANGU_MODE', 'sandbox'))

    digits_only = re.sub(r'\D', '', phone)
    formats = {'original': phone, 'digits_only': digits_only}

    if not digits_only.startswith('0') and len(digits_only) >= 9:
        formats['with_zero'] = '0' + digits_only[-9:]

    if len(digits_only) >= 9:
        formats['with_265'] = '+265' + digits_only[-9:]
        formats['nine_digits'] = digits_only[-9:]

    results = {}
    for fmt_name, fmt_value in formats.items():
        operator_id = paychangu.get_operator_id(fmt_value)
        cleaned = re.sub(r'\D', '', str(fmt_value))
        if cleaned.startswith('265'):
            cleaned = cleaned[3:]
        if cleaned.startswith('0'):
            cleaned = cleaned[1:]
        prefix = cleaned[:3] if len(cleaned) >= 3 else cleaned

        results[fmt_name] = {
            'input': fmt_value,
            'operator_id': operator_id,
            'detected': bool(operator_id),
            'prefix': prefix,
            'operator': 'Airtel' if operator_id and 'airtel' in operator_id.lower() else 'TNM' if operator_id else 'Unknown'
        }

    mapping = {
        'airtel_prefixes': ['098', '099', '088'],
        'tnm_prefixes': ['088', '089'],
        'airtel_id': '20be6c20-adeb-4b5b-a7ba-0769820df4fb',
        'tnm_id': 'f3d8b6c9-1a2b-3c4d-5e6f-7a8b9c0d1e2f'
    }

    return render_template('debug_phone.html', phone=phone, results=results, mapping=mapping)


@app.route('/debug-video/<int:lesson_id>')
@login_required
def debug_video(lesson_id):
    if not current_user.is_admin:
        return "Admin only", 403

    lesson = Lesson.query.get_or_404(lesson_id)

    def extract_method1(url):
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url
        return None

    def extract_method2(url):
        match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url)
        return match.group(1) if match else None

    def extract_method3(url):
        match = re.search(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})', url)
        return match.group(1) if match else None

    def extract_method4(url):
        match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]{11})', url)
        return match.group(1) if match else None

    video_id = None
    methods_tried = []

    if lesson.video_url:
        methods = [
            ('direct_id', extract_method1),
            ('youtu.be', extract_method2),
            ('watch?v=', extract_method3),
            ('embed', extract_method4)
        ]

        for method_name, method_func in methods:
            result = method_func(lesson.video_url)
            methods_tried.append({
                'method': method_name,
                'result': result,
                'success': result is not None
            })
            if result:
                video_id = result
                break

    return jsonify({
        'lesson_id': lesson.id,
        'lesson_title': lesson.title,
        'stored_url': lesson.video_url,
        'video_type': lesson.video_type,
        'extracted_video_id': video_id,
        'methods_tried': methods_tried,
        'embed_url': f'https://www.youtube.com/embed/{video_id}' if video_id else None
    })



@app.route('/db-health')
def db_health():
    """Check database connection"""
    try:
        # Try to execute a simple query
        from sqlalchemy import text
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'result': result
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@app.route('/fetch-operators')
@login_required
def fetch_operators():
    if not current_user.is_admin:
        return "Admin only", 403

    paychangu = PayChangu(mode=app.config.get('PAYCHANGU_MODE', 'sandbox'))

    try:
        response = requests.get(
            f"{paychangu.base_url}/api/v1/operators",
            headers=paychangu.get_headers(),
            timeout=30
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'message': 'Could not fetch from API, using hardcoded values',
                'operators': [
                    {'name': 'Airtel Money', 'id': '20be6c20-adeb-4b5b-a7ba-0769820df4fb',
                     'prefixes': ['098', '099', '088']},
                    {'name': 'TNM Mpamba', 'id': 'f3d8b6c9-1a2b-3c4d-5e6f-7a8b9c0d1e2f', 'prefixes': ['089', '088']}
                ]
            })
    except Exception as e:
        return jsonify({'error': str(e), 'using_hardcoded': True,
                        'operators': [
                            {'name': 'Airtel Money', 'id': '20be6c20-adeb-4b5b-a7ba-0769820df4fb'},
                            {'name': 'TNM Mpamba', 'id': 'f3d8b6c9-1a2b-3c4d-5e6f-7a8b9c0d1e2f'}
                        ]})


@app.route('/admin/test-webhook', methods=['POST'])
@login_required
def admin_test_webhook():
    """Admin route to manually trigger webhook for testing"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    reference = data.get('reference')

    if not reference:
        return jsonify({'error': 'Reference required'}), 400

    # Find payment
    payment = Payment.query.filter_by(reference=reference).first()
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404

    # Simulate webhook
    with app.test_client() as client:
        webhook_data = {
            'event_type': 'api.charge.payment',
            'status': 'success',
            'reference': reference,
            'charge_id': payment.charge_id or 'test_123',
            'trans_id': f"TRANS_{reference}"
        }

        response = client.post('/paychangu-webhook',
                               json=webhook_data,
                               headers={'Content-Type': 'application/json'})

        return jsonify({
            'message': 'Webhook triggered',
            'status_code': response.status_code,
            'response': response.json()
        })


# Test routes
@app.route('/test-paychangu')
def test_paychangu():
    paychangu = PayChangu(mode=app.config['PAYCHANGU_MODE'])
    test_payment = paychangu.initiate_mobile_money_payment(
        amount=100,
        phone_number='0999123456',
        email='test@example.com',
        name='Test User',
        reference=f"TEST-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    )
    return jsonify(test_payment)


@app.route('/test-paychangu-simple')
def test_paychangu_simple():
    try:
        response = requests.get("https://sandbox.paychangu.com", timeout=10)
        return f"PayChangu Sandbox is {'reachable' if response.status_code == 200 else 'returned status ' + str(response.status_code)}"
    except Exception as e:
        return f"Error connecting to PayChangu: {str(e)}"


@app.route('/stream/<int:lesson_id>')
@login_required
def stream_lesson(lesson_id):
    """Stream video/audio files"""
    lesson = Lesson.query.get_or_404(lesson_id)

    # Check access
    if not current_user.has_access(lesson.form) and not lesson.is_free:
        abort(403)

    if not lesson.file_path or lesson.content_type not in ['video', 'audio']:
        abort(404)

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], lesson.file_path)
    if not os.path.exists(file_path):
        abort(404)

    # Determine mime type
    mime_types = {
        'mp4': 'video/mp4', 'avi': 'video/x-msvideo', 'mov': 'video/quicktime',
        'mp3': 'audio/mpeg', 'wav': 'audio/wav', 'm4a': 'audio/mp4',
        'pdf': 'application/pdf', 'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    mime = mime_types.get(lesson.file_extension, 'application/octet-stream')

    return send_file(
        file_path,
        mimetype=mime,
        as_attachment=False,
        download_name=lesson.file_name
    )


@app.route('/download/<int:lesson_id>')
@login_required
def download_lesson(lesson_id):
    """Download files (only if downloadable=True)"""
    lesson = Lesson.query.get_or_404(lesson_id)

    if not current_user.has_access(lesson.form) and not lesson.is_free:
        abort(403)

    if not lesson.downloadable or not lesson.file_path:
        flash('This file is not available for download', 'danger')
        return redirect(url_for('view_lesson', lesson_id=lesson.id))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], lesson.file_path)
    if not os.path.exists(file_path):
        abort(404)

    return send_file(
        file_path,
        as_attachment=True,
        download_name=lesson.file_name,
        mimetype='application/octet-stream'
    )


@app.route('/test-email')
def test_email():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    success, message = test_smtp_connection()

    if success:
        flash(f'SMTP Test: {message}', 'success')
    else:
        flash(f'SMTP Test Failed: {message}', 'danger')

    return redirect(url_for('admin_dashboard'))


@app.route('/api/lesson/<int:lesson_id>/progress', methods=['POST'])
@login_required
def update_lesson_progress(lesson_id):
    """Update watch progress for a lesson"""
    try:
        data = request.json
        watch_time = data.get('watch_time', 0)
        video_duration = data.get('duration', 0)

        # Find or create progress record
        progress = Progress.query.filter_by(
            user_id=current_user.id,
            lesson_id=lesson_id
        ).first()

        if not progress:
            progress = Progress(
                user_id=current_user.id,
                lesson_id=lesson_id,
                watch_time=watch_time,
                last_watched=datetime.utcnow()
            )
            db.session.add(progress)
        else:
            progress.watch_time = watch_time
            progress.last_watched = datetime.utcnow()

        # Mark as completed if watched 90% or more
        if video_duration > 0 and (watch_time / video_duration) >= 0.9:
            progress.completed = True

        db.session.commit()

        # Calculate progress percentage
        percentage = 0
        if video_duration > 0:
            percentage = min(100, int((watch_time / video_duration) * 100))

        return jsonify({
            'success': True,
            'progress': percentage,
            'completed': progress.completed
        })
    except Exception as e:
        print(f"Error saving progress: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/lesson/<int:lesson_id>/progress', methods=['GET'])
@login_required
def get_lesson_progress(lesson_id):
    """Get progress for a specific lesson"""
    try:
        progress = Progress.query.filter_by(
            user_id=current_user.id,
            lesson_id=lesson_id
        ).first()

        lesson = Lesson.query.get_or_404(lesson_id)

        percentage = 0
        watch_time = 0
        completed = False

        if progress:
            watch_time = progress.watch_time
            completed = progress.completed
            if lesson.duration and lesson.duration > 0:
                percentage = min(100, int((progress.watch_time / (lesson.duration * 60)) * 100))

        return jsonify({
            'progress': percentage,
            'completed': completed,
            'watch_time': watch_time
        })
    except Exception as e:
        print(f"Error getting progress: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/progress', methods=['GET'])
@login_required
def get_user_progress():
    """Get all progress for current user"""
    progress_entries = Progress.query.filter_by(user_id=current_user.id).all()

    result = []
    for p in progress_entries:
        lesson = Lesson.query.get(p.lesson_id)
        if lesson:
            percentage = 0
            if lesson.duration > 0:
                percentage = min(100, int((p.watch_time / (lesson.duration * 60)) * 100))

            result.append({
                'lesson_id': p.lesson_id,
                'lesson_title': lesson.title,
                'subject': lesson.subject.name,
                'progress': percentage,
                'completed': p.completed,
                'last_watched': p.last_watched.isoformat() if p.last_watched else None
            })

    return jsonify(result)





# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.route('/health')
def health():
    """Health check for Render"""
    return jsonify({'status': 'healthy', 'time': datetime.utcnow().isoformat()})

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


# Add this near the bottom of app.py, before if __name__ == '__main__'
with app.app_context():
    try:
        # Test database connection
        from sqlalchemy import text
        db.session.execute(text('SELECT 1')).scalar()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("⚠️  Continuing startup - app may not function correctly")



if __name__ == '__main__':
    app.run(debug=True)