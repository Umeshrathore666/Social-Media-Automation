import requests
from config import Config
from error_handlers import with_ai_error_handling
from logger_config import get_logger

logger = get_logger('facebook_publisher')

def create_facebook_session(access_token):
    session = requests.Session()
    session.params.update({'access_token': access_token})
    return session

def get_user_pages(session):
    pages_url = 'https://graph.facebook.com/v18.0/me/accounts'
    response = session.get(pages_url)
    
    if response.status_code == 200:
        pages_data = response.json()
        pages = pages_data.get('data', [])
        logger.info(f"Retrieved {len(pages)} Facebook pages")
        return pages
    else:
        logger.error(f"Failed to get Facebook pages: {response.status_code}")
        raise Exception(f"Facebook API error: {response.status_code}")

def upload_image_to_facebook(session, page_id, image_path):
    upload_url = f'https://graph.facebook.com/v18.0/{page_id}/photos'
    
    with open(image_path, 'rb') as image_file:
        files = {'source': image_file}
        data = {'published': 'false'}
        
        response = session.post(upload_url, files=files, data=data)
        
        if response.status_code == 200:
            upload_data = response.json()
            photo_id = upload_data.get('id')
            logger.info(f"Image uploaded to Facebook: {photo_id}")
            return photo_id
        else:
            logger.error(f"Failed to upload image to Facebook: {response.status_code}")
            raise Exception(f"Facebook image upload failed: {response.status_code}")

@with_ai_error_handling('facebook_post_creation')
def create_facebook_post(access_token, content, image_path=None, page_id=None):
    session = create_facebook_session(access_token)
    
    if not page_id:
        pages = get_user_pages(session)
        if pages:
            page_id = pages[0]['id']
        else:
            raise Exception("No Facebook pages found")
    
    post_url = f'https://graph.facebook.com/v18.0/{page_id}/feed'
    post_data = {'message': content}
    
    if image_path:
        photo_id = upload_image_to_facebook(session, page_id, image_path)
        post_data['object_attachment'] = photo_id
    
    response = session.post(post_url, data=post_data)
    
    if response.status_code == 200:
        post_response = response.json()
        post_id = post_response.get('id')
        logger.info(f"Facebook post created successfully: {post_id}")
        return post_id
    else:
        logger.error(f"Failed to create Facebook post: {response.status_code}")
        raise Exception(f"Facebook posting failed: {response.status_code}")

def get_facebook_auth_url():
    facebook_auth_url = "https://www.facebook.com/v18.0/dialog/oauth"
    params = {
        'client_id': Config.FACEBOOK_APP_ID,
        'redirect_uri': 'http://localhost:5000/auth/facebook/callback',
        'state': 'facebook_auth',
        'scope': 'pages_manage_posts,pages_read_engagement,publish_to_groups'
    }
    
    auth_url = f"{facebook_auth_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    return auth_url

def exchange_code_for_token(code):
    token_url = 'https://graph.facebook.com/v18.0/oauth/access_token'
    
    token_params = {
        'client_id': Config.FACEBOOK_APP_ID,
        'client_secret': Config.FACEBOOK_APP_SECRET,
        'redirect_uri': 'http://localhost:5000/auth/facebook/callback',
        'code': code
    }
    
    response = requests.get(token_url, params=token_params)
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access_token')
        logger.info("Facebook access token obtained successfully")
        return access_token
    else:
        logger.error(f"Failed to get Facebook access token: {response.status_code}")
        raise Exception(f"Facebook token exchange failed: {response.status_code}")