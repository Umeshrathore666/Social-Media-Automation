from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
from models import Post, db
from error_handlers import with_database_error_handling
from logger_config import get_logger
import atexit

scheduler = BackgroundScheduler()
logger = get_logger('scheduler')

def simulate_post_to_platform(post_id, platform):
    try:
        post = Post.query.get(post_id)
        if post:
            post.status = 'posted'
            post.posted_at = datetime.utcnow()
            db.session.commit()
            logger.info(f"Simulated post to {platform} for post {post_id}")
            return True
        return False
    except Exception as error:
        logger.error(f"Failed to simulate post to {platform}: {str(error)}")
        return False

def execute_scheduled_post(post_id):
    logger.info(f"Executing scheduled post {post_id}")
    post = Post.query.get(post_id)
    if not post:
        logger.error(f"Post {post_id} not found for execution")
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
            logger.info(f"Post {post_id} executed successfully on {success_count} platforms")
        else:
            post.status = 'failed'
            post.error_message = 'Failed to post to any platform'
            logger.error(f"Post {post_id} failed to execute on any platform")
        
        db.session.commit()
    except Exception as error:
        post.status = 'failed'
        post.error_message = str(error)
        db.session.commit()
        logger.error(f"Error executing scheduled post {post_id}: {str(error)}")

def schedule_post(post_id, scheduled_time):
    job_id = f"post_{post_id}"
    
    try:
        scheduler.add_job(
            func=execute_scheduled_post,
            trigger=DateTrigger(run_date=scheduled_time),
            args=[post_id],
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Post {post_id} scheduled for {scheduled_time}")
        return job_id
    except Exception as error:
        logger.error(f"Failed to schedule post {post_id}: {str(error)}")
        raise

def cancel_scheduled_post(post_id):
    job_id = f"post_{post_id}"
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Cancelled scheduled post {post_id}")
        return True
    except Exception as error:
        logger.warning(f"Failed to cancel scheduled post {post_id}: {str(error)}")
        return False

def start_scheduler():
    try:
        scheduler.start()
        logger.info("Scheduler started successfully")
        atexit.register(lambda: scheduler.shutdown())
    except Exception as error:
        logger.error(f"Failed to start scheduler: {str(error)}")
        raise