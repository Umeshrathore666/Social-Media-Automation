import requests
from config import Config
from error_handlers import with_ai_error_handling
from logger_config import get_logger

logger = get_logger('instagram_publisher')

def create_instagram_session(access_token):
    session = requests.Session()
    session.params.update({'access_token': access_token})
    return session

def get_instagram_business_account(session):
    accounts_url = 'https://graph.facebook.com/v18.0/me/accounts'
    response = session.get(accounts_url)
    
    if response.status_code == 200:
        accounts_data = response.json()
        for account in accounts_data.get('data', []):
            page_id = account['id']
            instagram_url = f'https://graph.facebook.com/v18.0/{page_id}?fields=instagram_business_account'
            ig_response = session.get(instagram_url)
            
            if ig_response.status_code == 200:
                ig_data = ig_response.json()
                if 'instagram_business_account' in ig_data:
                    ig_account_id = ig_data['instagram_business_account']['id']
                    logger.info(f"Found Instagram business account: {ig_account_id}")
                    return ig_account_id
    
    raise Exception("No Instagram business account found")

def upload_image_to_instagram(session, ig_account_id, image_url, caption):
    create_url = f'https://graph.facebook.com/v18.0/{ig_account_id}/media'
    
    create_data = {
        'image_url': image_url,
        'caption': caption
    }
    
    response = session.post(create_url, data=create_data)
    
    if response.status_code == 200:
        creation_data = response.json()
        creation_id = creation_data.get('id')
        logger.info(f"Instagram media created: {creation_id}")
        return creation_id
    else:
        logger.error(f"Failed to create Instagram media: {response.status_code}")
        raise Exception(f"Instagram media creation failed: {response.status_code}")

def publish_instagram_media(session, ig_account_id, creation_id):
    publish_url = f'https://graph.facebook.com/v18.0/{ig_account_id}/media_publish'
    
    publish_data = {'creation_id': creation_id}
    response = session.post(publish_url, data=publish_data)
    
    if response.status_code == 200:
        publish_data = response.json()
        media_id = publish_data.get('id')
        logger.info(f"Instagram post published: {media_id}")
        return media_id
    else:
        logger.error(f"Failed to publish Instagram media: {response.status_code}")
        raise Exception(f"Instagram publishing failed: {response.status_code}")

@with_ai_error_handling('instagram_post_creation')
def create_instagram_post(access_token, content, image_url):
    session = create_instagram_session(access_token)
    ig_account_id = get_instagram_business_account(session)
    
    creation_id = upload_image_to_instagram(session, ig_account_id, image_url, content)
    media_id = publish_instagram_media(session, ig_account_id, creation_id)
    
    logger.info(f"Instagram post created successfully: {media_id}")
    return media_id