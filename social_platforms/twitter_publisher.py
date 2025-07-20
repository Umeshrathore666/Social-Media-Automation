import tweepy
from config import Config
from error_handlers import with_ai_error_handling
from logger_config import get_logger

logger = get_logger('twitter_publisher')

def create_twitter_client():
    auth = tweepy.OAuthHandler(Config.TWITTER_API_KEY, Config.TWITTER_API_SECRET)
    auth.set_access_token(Config.TWITTER_ACCESS_TOKEN, Config.TWITTER_ACCESS_TOKEN_SECRET)
    
    api = tweepy.API(auth, wait_on_rate_limit=True)
    client = tweepy.Client(
        consumer_key=Config.TWITTER_API_KEY,
        consumer_secret=Config.TWITTER_API_SECRET,
        access_token=Config.TWITTER_ACCESS_TOKEN,
        access_token_secret=Config.TWITTER_ACCESS_TOKEN_SECRET,
        wait_on_rate_limit=True
    )
    
    logger.info("Twitter client created successfully")
    return api, client

def upload_image_to_twitter(api, image_path):
    media = api.media_upload(image_path)
    media_id = media.media_id
    logger.info(f"Image uploaded to Twitter: {media_id}")
    return media_id

@with_ai_error_handling('twitter_post_creation')
def create_twitter_post(content, image_path=None):
    api, client = create_twitter_client()
    
    media_ids = None
    if image_path:
        media_id = upload_image_to_twitter(api, image_path)
        media_ids = [media_id]
    
    tweet = client.create_tweet(text=content, media_ids=media_ids)
    
    if tweet.data:
        tweet_id = tweet.data['id']
        logger.info(f"Twitter post created successfully: {tweet_id}")
        return tweet_id
    else:
        logger.error("Failed to create Twitter post")
        raise Exception("Twitter posting failed")

def verify_twitter_credentials():
    try:
        api, client = create_twitter_client()
        user = api.verify_credentials()
        if user:
            logger.info(f"Twitter credentials verified for user: {user.screen_name}")
            return True
        return False
    except Exception as error:
        logger.error(f"Twitter credentials verification failed: {str(error)}")
        return False