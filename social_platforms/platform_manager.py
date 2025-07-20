import os
from config import get_upload_folder
from error_handlers import with_ai_error_handling
from logger_config import get_logger
from .linkedin_publisher import create_linkedin_post
from .twitter_publisher import create_twitter_post
from .facebook_publisher import create_facebook_post
from .instagram_publisher import create_instagram_post

logger = get_logger('platform_manager')

def get_local_image_path(image_url):
    if image_url.startswith('/static/generated_images/'):
        filename = image_url.split('/')[-1]
        upload_folder = get_upload_folder()
        local_path = os.path.join(upload_folder, filename)
        
        if os.path.exists(local_path):
            logger.info(f"Found local image: {local_path}")
            return local_path
    
    logger.warning(f"Local image not found for URL: {image_url}")
    return None

def get_full_image_url(image_url, base_url='http://localhost:5000'):
    if image_url.startswith('/static/'):
        full_url = f"{base_url}{image_url}"
        logger.info(f"Generated full image URL: {full_url}")
        return full_url
    return image_url

@with_ai_error_handling('platform_posting')
def post_to_platform(platform, access_token, content, image_url=None):
    platform_handlers = {
        'LinkedIn': post_to_linkedin,
        'Twitter': post_to_twitter,
        'Facebook': post_to_facebook,
        'Instagram': post_to_instagram
    }
    
    handler = platform_handlers.get(platform)
    if not handler:
        raise Exception(f"Unsupported platform: {platform}")
    
    logger.info(f"Posting to {platform}")
    result = handler(access_token, content, image_url)
    logger.info(f"Successfully posted to {platform}: {result}")
    return result

def post_to_linkedin(access_token, content, image_url=None):
    image_path = None
    if image_url:
        image_path = get_local_image_path(image_url)
    
    return create_linkedin_post(access_token, content, image_path)

def post_to_twitter(access_token, content, image_url=None):
    image_path = None
    if image_url:
        image_path = get_local_image_path(image_url)
    
    return create_twitter_post(content, image_path)

def post_to_facebook(access_token, content, image_url=None):
    image_path = None
    if image_url:
        image_path = get_local_image_path(image_url)
    
    return create_facebook_post(access_token, content, image_path)

def post_to_instagram(access_token, content, image_url=None):
    if not image_url:
        raise Exception("Instagram posts require an image")
    
    full_image_url = get_full_image_url(image_url)
    return create_instagram_post(access_token, content, full_image_url)

def validate_platform_requirements(platform, content, image_url):
    if platform == 'Instagram' and not image_url:
        return False, "Instagram posts require an image"
    
    if platform == 'Twitter' and len(content) > 280:
        return False, "Twitter posts must be under 280 characters"
    
    return True, None