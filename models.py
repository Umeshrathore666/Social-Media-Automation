from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from logger_config import get_logger

db = SQLAlchemy()
logger = get_logger('models')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    accounts = db.relationship('SocialAccount', backref='user', lazy=True)
    posts = db.relationship('Post', backref='user', lazy=True)

class SocialAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    access_token = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    platforms = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')
    scheduled_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posted_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)

def init_database_tables():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as error:
        logger.error(f"Failed to create database tables: {str(error)}")
        raise

def create_sample_accounts_for_user(user_id, username):
    try:
        existing_accounts = SocialAccount.query.filter_by(user_id=user_id).first()
        if not existing_accounts:
            platforms = ['LinkedIn', 'Twitter', 'Instagram', 'Facebook']
            for platform in platforms:
                account = SocialAccount(
                    user_id=user_id,
                    platform=platform,
                    account_name=f"{username}_{platform.lower()}",
                    access_token=None,
                    is_active=True
                )
                db.session.add(account)
            db.session.commit()
            logger.info(f"Created sample accounts for user {user_id}")
            return True
        else:
            logger.info(f"Sample accounts already exist for user {user_id}")
            return False
    except Exception as error:
        logger.error(f"Failed to create sample accounts: {str(error)}")
        db.session.rollback()
        raise

def ensure_user_has_accounts(user_id, username):
    account_count = SocialAccount.query.filter_by(user_id=user_id).count()
    if account_count == 0:
        create_sample_accounts_for_user(user_id, username)
        logger.info(f"Ensured accounts exist for user {user_id}")

def init_db():
    init_database_tables()