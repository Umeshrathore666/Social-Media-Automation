from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_required, current_user
from datetime import datetime
import json

from config import Config
from models import db, User, SocialAccount, Post, init_db
from auth import auth_bp
from ai_service import generate_complete_post
from scheduler import start_scheduler, schedule_post, cancel_scheduled_post

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app.register_blueprint(auth_bp, url_prefix='/auth')

def get_user_accounts():
    return SocialAccount.query.filter_by(user_id=current_user.id, is_active=True).all()

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
    return post

def process_post_submission(content, image_url, selected_accounts, schedule_datetime):
    platforms = [acc.platform for acc in selected_accounts]
    
    if schedule_datetime:
        post = create_post_record(content, image_url, platforms, schedule_datetime)
        schedule_post(post.id, schedule_datetime)
        flash(f'Post scheduled for {schedule_datetime.strftime("%Y-%m-%d %H:%M")}', 'success')
    else:
        post = create_post_record(content, image_url, platforms)
        post.status = 'posted'
        post.posted_at = datetime.utcnow()
        db.session.commit()
        flash('Post published successfully!', 'success')

@app.route('/')
def index():
    return redirect(url_for('auth.login'))

@app.route('/dashboard')
@login_required
def dashboard():
    recent_posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.created_at.desc()).limit(5).all()
    accounts = get_user_accounts()
    
    stats = {
        'total_posts': Post.query.filter_by(user_id=current_user.id).count(),
        'scheduled_posts': Post.query.filter_by(user_id=current_user.id, status='scheduled').count(),
        'connected_accounts': len(accounts)
    }
    
    return render_template('dashboard.html', recent_posts=recent_posts, accounts=accounts, stats=stats)

@app.route('/new_post', methods=['GET', 'POST'])
@login_required
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
def post_history():
    posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.created_at.desc()).all()
    return render_template('post_history.html', posts=posts)

@app.route('/account_settings')
@login_required
def account_settings():
    accounts = get_user_accounts()
    return render_template('account_settings.html', accounts=accounts)

@app.route('/cancel_post/<int:post_id>')
@login_required
def cancel_post(post_id):
    post = Post.query.filter_by(id=post_id, user_id=current_user.id).first()
    if post and post.status == 'scheduled':
        cancel_scheduled_post(post_id)
        post.status = 'cancelled'
        db.session.commit()
        flash('Scheduled post cancelled successfully', 'success')
    return redirect(url_for('post_history'))

if __name__ == '__main__':
    with app.app_context():
        init_db()
    start_scheduler()
    app.run(debug=True)