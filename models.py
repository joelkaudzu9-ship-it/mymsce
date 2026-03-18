# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)  # For mobile money
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)  # Email verified
    is_active_subscriber = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False)
    subscription_type = db.Column(db.String(20), default='none')
    subscription_form = db.Column(db.String(20), default='none')  # form3, form4, combined
    subscription_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payments = db.relationship('Payment', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_access(self, form_number):
        """Check if user has access to specific form"""
        if not self.is_active_subscriber or not self.subscription_expiry:
            return False
        if self.subscription_expiry < datetime.utcnow():
            return False
        if self.subscription_form == 'combined':
            return True
        if self.subscription_form == f'form{form_number}':
            return True
        return False

    def get_subscription_days_left(self):
        if not self.subscription_expiry:
            return 0
        delta = self.subscription_expiry - datetime.utcnow()
        return max(0, delta.days)


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    form = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='book')
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # This creates the backref to lessons
    #lessons = db.relationship('Lesson', backref='subject', lazy=True, cascade='all, delete-orphan')


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text)  # HTML content

    # File fields
    content_type = db.Column(db.String(20), default='video')  # video, audio, document, presentation
    file_path = db.Column(db.String(500))  # Path to uploaded file
    file_name = db.Column(db.String(200))  # Original filename
    file_size = db.Column(db.Integer, default=0)  # Size in bytes
    file_extension = db.Column(db.String(10))  # .mp4, .mp3, .pdf, etc.

    # For external videos (YouTube/Vimeo fallback)
    video_url = db.Column(db.String(500))
    video_type = db.Column(db.String(20), default='youtube')

    downloadable = db.Column(db.Boolean, default=False)  # Can students download?
    duration = db.Column(db.Integer, default=0)  # in minutes
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    form = db.Column(db.Integer, nullable=False)
    order = db.Column(db.Integer, default=0)
    is_free = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    subject = db.relationship('Subject', backref=db.backref('lessons', lazy=True, cascade='all, delete-orphan'))


# models.py - Add/update this model

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    watch_time = db.Column(db.Integer, default=0)  # seconds watched
    last_watched = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='progress_entries')
    lesson = db.relationship('Lesson', backref='progress_entries')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'lesson_id', name='unique_user_lesson'),
    )


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='MWK')
    payment_method = db.Column(db.String(50))  # airtel, tnm
    phone_number = db.Column(db.String(20))

    # PayChangu fields
    charge_id = db.Column(db.String(100), unique=True)  # PayChangu charge ID
    transaction_id = db.Column(db.String(100), unique=True)  # PayChangu transaction ID
    reference = db.Column(db.String(100), unique=True)  # Our reference

    subscription_type = db.Column(db.String(20))  # daily, weekly, monthly
    subscription_form = db.Column(db.String(20))  # form3, form4, combined
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    paychangu_response = db.Column(db.Text)  # Store full response for debugging

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def get_days_for_subscription(self):
        """Get number of days for subscription type"""
        days_map = {
            'daily': 1,
            'weekly': 7,
            'monthly': 30
        }
        return days_map.get(self.subscription_type, 0)


class EmailVerification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24))
    used = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='verification_tokens')


class PasswordReset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=1))
    used = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='reset_tokens')