from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
from models import Post, db
import atexit

scheduler = BackgroundScheduler()

def simulate_post_to_platform(post_id, platform):
    post = Post.query.get(post_id)
    if post:
        post.status = 'posted'
        post.posted_at = datetime.utcnow()
        db.session.commit()
        return True
    return False

def execute_scheduled_post(post_id):
    post = Post.query.get(post_id)
    if not post:
        return
    
    try:
        platforms = post.platforms.split(',') if post.platforms else []
        success_count = 0
        
        for platform in platforms:
            if simulate_post_to_platform(post_id, platform.strip()):
                success_count += 1
        
        if success_count > 0:
            post.status = 'posted'
            post.posted_at = datetime.utcnow()
        else:
            post.status = 'failed'
            post.error_message = 'Failed to post to any platform'
        
        db.session.commit()
    except Exception as e:
        post.status = 'failed'
        post.error_message = str(e)
        db.session.commit()

def schedule_post(post_id, scheduled_time):
    job_id = f"post_{post_id}"
    
    scheduler.add_job(
        func=execute_scheduled_post,
        trigger=DateTrigger(run_date=scheduled_time),
        args=[post_id],
        id=job_id,
        replace_existing=True
    )
    
    return job_id

def cancel_scheduled_post(post_id):
    job_id = f"post_{post_id}"
    try:
        scheduler.remove_job(job_id)
        return True
    except:
        return False

def start_scheduler():
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())