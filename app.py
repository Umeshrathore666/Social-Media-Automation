from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_required, current_user
from datetime import datetime
import json
import os

from config import Config, get_upload_folder
from models import db, User, SocialAccount, Post, init_db, ensure_user_has_accounts
from auth import auth_bp
from ai_service import generate_complete_post
from scheduler import start_scheduler, schedule_post, cancel_scheduled_post
from error_handlers import with_error_handling, with_database_error_handling
from logger_config import setup_application_logger, get_logger
from image_generation import cleanup_old_images
from social_platforms.platform_manager import post_to_platform, validate_platform_requirements
from social_platforms.linkedin_publisher import get_linkedin_auth_url, exchange_code_for_token as linkedin_exchange
from social_platforms.facebook_publisher import get_facebook_auth_url, exchange_code_for_token as facebook_exchange

app = Flask(__name__)
app.config.from_object(Config)

setup_application_logger()
logger = get_logger('main')

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app.register_blueprint(auth_bp, url_prefix='/auth')

@app.route('/static/generated_images/<filename>')
def serve_generated_image(filename):
    upload_folder = get_upload_folder()
    return send_from_directory(upload_folder, filename)

def get_user_accounts():
    ensure_user_has_accounts(current_user.id, current_user.username)
    accounts = SocialAccount.query.filter_by(user_id=current_user.id, is_active=True).all()
    logger.info(f"Retrieved {len(accounts)} accounts for user {current_user.id}")
    return accounts

def create_post_record(content, image_url, platforms, scheduled_time=None):
    platforms_str = ','.join(platforms) if platforms else ''
    status = 'scheduled' if scheduled_time else 'posted'
    
    post = Post(
        user_id=current_user.id,
        content=content,
        image_url=image_url,
        platforms=platforms_str,
        status=status,
        scheduled_time=scheduled_time
    )
    
    db.session.add(post)
    db.session.commit()
    logger.info(f"Post record created with ID {post.id} for user {current_user.id}")
    return post

def publish_post_immediately(content, image_url, selected_accounts):
    success_count = 0
    failed_platforms = []
    
    for account in selected_accounts:
        try:
            is_valid, error_msg = validate_platform_requirements(account.platform, content, image_url)
            if not is_valid:
                failed_platforms.append(f"{account.platform}: {error_msg}")
                continue
            
            if account.access_token:
                result = post_to_platform(account.platform, account.access_token, content, image_url)
                if result:
                    success_count += 1
                else:
                    failed_platforms.append(account.platform)
            else:
                failed_platforms.append(f"{account.platform}: No access token - connect account first")
        except Exception as error:
            failed_platforms.append(f"{account.platform}: {str(error)}")
            logger.error(f"Failed to post to {account.platform}: {str(error)}")
    
    return success_count, failed_platforms

def process_post_submission(content, image_url, selected_accounts, schedule_datetime):
    platforms = [acc.platform for acc in selected_accounts]
    
    if schedule_datetime:
        post = create_post_record(content, image_url, platforms, schedule_datetime)
        schedule_post(post.id, schedule_datetime)
        flash(f'Post scheduled for {schedule_datetime.strftime("%Y-%m-%d %H:%M")}', 'success')
        logger.info(f"Post {post.id} scheduled for {schedule_datetime}")
    else:
        success_count, failed_platforms = publish_post_immediately(content, image_url, selected_accounts)
        
        post = create_post_record(content, image_url, platforms)
        
        if success_count > 0:
            post.status = 'posted'
            post.posted_at = datetime.utcnow()
            if failed_platforms:
                post.error_message = f"Failed on: {', '.join(failed_platforms)}"
            flash(f'Post published successfully to {success_count} platforms!', 'success')
            if failed_platforms:
                flash(f'Failed on: {", ".join(failed_platforms)}', 'error')
        else:
            post.status = 'failed'
            post.error_message = f'Failed on all platforms: {", ".join(failed_platforms)}'
            flash('Post failed to publish. Please connect your social media accounts first.', 'error')
        
        db.session.commit()
        logger.info(f"Post {post.id} published to {success_count} platforms")

def get_dashboard_stats():
    stats = {
        'total_posts': Post.query.filter_by(user_id=current_user.id).count(),
        'scheduled_posts': Post.query.filter_by(user_id=current_user.id, status='scheduled').count(),
        'connected_accounts': len([acc for acc in get_user_accounts() if acc.access_token])
    }
    return stats

def perform_maintenance_tasks():
    try:
        cleanup_old_images()
        logger.info("Maintenance tasks completed")
    except Exception as error:
        logger.error(f"Maintenance tasks failed: {str(error)}")

def ensure_static_directories():
    static_dir = os.path.join(app.root_path, 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    upload_dir = get_upload_folder()
    logger.info(f"Static directories ensured: {upload_dir}")

@app.route('/')
def index():
    return redirect(url_for('auth.login'))

@app.route('/dashboard')
@login_required
@with_database_error_handling('dashboard_load', 'auth.login')
def dashboard():
    recent_posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.created_at.desc()).limit(5).all()
    accounts = get_user_accounts()
    stats = get_dashboard_stats()
    
    return render_template('dashboard.html', recent_posts=recent_posts, accounts=accounts, stats=stats)

@app.route('/new_post', methods=['GET', 'POST'])
@login_required
@with_error_handling('new_post_page', 'dashboard')
def new_post():
    accounts = get_user_accounts()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'generate':
            platform = request.form.get('platform', 'LinkedIn')
            topic = request.form.get('topic', '')
            
            if topic:
                generated_post = generate_complete_post(platform, topic)
                return render_template('new_post.html', accounts=accounts, generated_post=generated_post, topic=topic, platform=platform)
            else:
                flash('Please enter a topic for post generation', 'error')
        
        elif action == 'publish':
            content = request.form.get('content')
            image_url = request.form.get('image_url')
            selected_account_ids = request.form.getlist('selected_accounts')
            schedule_date = request.form.get('schedule_date')
            schedule_time = request.form.get('schedule_time')
            
            if not content or not selected_account_ids:
                flash('Please provide content and select at least one account', 'error')
                return render_template('new_post.html', accounts=accounts)
            
            selected_accounts = SocialAccount.query.filter(SocialAccount.id.in_(selected_account_ids)).all()
            
            schedule_datetime = None
            if schedule_date and schedule_time:
                schedule_datetime = datetime.strptime(f"{schedule_date} {schedule_time}", "%Y-%m-%d %H:%M")
            
            process_post_submission(content, image_url, selected_accounts, schedule_datetime)
            return redirect(url_for('dashboard'))
    
    return render_template('new_post.html', accounts=accounts)

@app.route('/post_history')
@login_required
@with_database_error_handling('post_history_load', 'dashboard')
def post_history():
    posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.created_at.desc()).all()
    return render_template('post_history.html', posts=posts)

@app.route('/account_settings')
@login_required
@with_database_error_handling('account_settings_load', 'dashboard')
def account_settings():
    accounts = get_user_accounts()
    linkedin_auth_url = get_linkedin_auth_url()
    facebook_auth_url = get_facebook_auth_url()
    
    return render_template('account_settings.html', accounts=accounts, 
                         linkedin_auth_url=linkedin_auth_url, 
                         facebook_auth_url=facebook_auth_url)

@app.route('/auth/linkedin/callback')
@login_required
def linkedin_callback():
    code = request.args.get('code')
    if code:
        try:
            access_token = linkedin_exchange(code)
            
            account = SocialAccount.query.filter_by(
                user_id=current_user.id,
                platform='LinkedIn'
            ).first()
            
            if account:
                account.access_token = access_token
            else:
                account = SocialAccount(
                    user_id=current_user.id,
                    platform='LinkedIn',
                    account_name=f"{current_user.username}_linkedin",
                    access_token=access_token
                )
                db.session.add(account)
            
            db.session.commit()
            flash('LinkedIn account connected successfully!', 'success')
        except Exception as error:
            flash(f'LinkedIn connection failed: {str(error)}', 'error')
    
    return redirect(url_for('account_settings'))

@app.route('/auth/facebook/callback')
@login_required
def facebook_callback():
    code = request.args.get('code')
    if code:
        try:
            access_token = facebook_exchange(code)
            
            account = SocialAccount.query.filter_by(
                user_id=current_user.id,
                platform='Facebook'
            ).first()
            
            if account:
                account.access_token = access_token
            else:
                account = SocialAccount(
                    user_id=current_user.id,
                    platform='Facebook',
                    account_name=f"{current_user.username}_facebook",
                    access_token=access_token
                )
                db.session.add(account)
            
            db.session.commit()
            flash('Facebook account connected successfully!', 'success')
        except Exception as error:
            flash(f'Facebook connection failed: {str(error)}', 'error')
    
    return redirect(url_for('account_settings'))

@app.route('/cancel_post/<int:post_id>')
@login_required
@with_database_error_handling('cancel_post', 'post_history')
def cancel_post(post_id):
    post = Post.query.filter_by(id=post_id, user_id=current_user.id).first()
    if post and post.status == 'scheduled':
        cancel_scheduled_post(post_id)
        post.status = 'cancelled'
        db.session.commit()
        flash('Scheduled post cancelled successfully', 'success')
        logger.info(f"Post {post_id} cancelled by user {current_user.id}")
    return redirect(url_for('post_history'))

@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 error: {request.url}")
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {str(error)}")
    db.session.rollback()
    return render_template('base.html'), 500

if __name__ == '__main__':
    with app.app_context():
        ensure_static_directories()
        init_db()
        perform_maintenance_tasks()
    start_scheduler()
    logger.info("Application started successfully with real social media posting")
    app.run(debug=True)