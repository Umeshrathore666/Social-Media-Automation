from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db
from error_handlers import with_database_error_handling, with_error_handling
from logger_config import get_logger

auth_bp = Blueprint('auth', __name__)
logger = get_logger('auth')

def validate_registration_data(username, email, password):
    if len(username) < 3:
        return "Username must be at least 3 characters long"
    if len(password) < 6:
        return "Password must be at least 6 characters long"
    if '@' not in email:
        return "Please enter a valid email address"
    return None

def create_new_user(username, email, password):
    password_hash = generate_password_hash(password)
    user = User(username=username, email=email, password_hash=password_hash)
    db.session.add(user)
    db.session.commit()
    logger.info(f"New user created: {username}")
    return user

def authenticate_user(username, password):
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        logger.info(f"User authenticated successfully: {username}")
        return user
    logger.warning(f"Authentication failed for username: {username}")
    return None

def check_existing_user(username):
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        logger.warning(f"Registration attempt with existing username: {username}")
        return True
    return False

@auth_bp.route('/register', methods=['GET', 'POST'])
@with_database_error_handling('user_registration', 'auth.register')
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        validation_error = validate_registration_data(username, email, password)
        if validation_error:
            flash(validation_error, 'error')
            return render_template('register.html')
        
        if check_existing_user(username):
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        user = create_new_user(username, email, password)
        login_user(user)
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
@with_error_handling('user_login', 'auth.login')
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = authenticate_user(username, password)
        if user:
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
@with_error_handling('user_logout', 'auth.login')
def logout():
    username = current_user.username
    logout_user()
    logger.info(f"User logged out: {username}")
    return redirect(url_for('auth.login'))