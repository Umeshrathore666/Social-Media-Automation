from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
from models import Post, SocialAccount, db
from error_handlers import with_database_error_handling
from logger_config import get_logger
from social_platforms.platform_manager import post_to_platform
import atexit

scheduler = BackgroundScheduler()
logger = get_logger('scheduler')

def get_account_access_token(account_id):
    account = SocialAccount.query.get(account_id)
    if account and account.access_token:
        return account.access_token
    return None

def post_to_single_platform(post_id, platform, account_id):
    try:
        post = Post.query.get(post_id)
        access_token = get_account_access_token(account_id)
        
        if not access_token:
            logger.error(f"No access token found for account {account_id}")
            return False
        
        result = post_to_platform(platform, access_token, post.content, post.image_url)
        
        if result:
            logger.info(f"Successfully posted to {platform} for post {post_id}")
            return True
        return False
    except Exception as error:
        logger.error(f"Failed to post to {platform}: {str(error)}")
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
        failed_platforms = []
        
        for platform_name in platforms:
            platform_name = platform_name.strip()
            account = SocialAccount.query.filter_by(
                user_id=post.user_id,
                platform=platform_name,
                is_active=True
            ).first()
            
            if account:
                if post_to_single_platform(post_id, platform_name, account.id):
                    success_count += 1
                else:
                    failed_platforms.append(platform_name)
            else:
                failed_platforms.append(platform_name)
                logger.warning(f"No active account found for platform {platform_name}")
        
        if success_count > 0:
            post.status = 'posted'
            post.posted_at = datetime.utcnow()
            if failed_platforms:
                post.error_message = f"Failed on platforms: {', '.join(failed_platforms)}"
            logger.info(f"Post {post_id} executed successfully on {success_count} platforms")
        else:
            post.status = 'failed'
            post.error_message = f'Failed to post to any platform: {", ".join(failed_platforms)}'
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
    