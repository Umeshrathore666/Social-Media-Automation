import requests
from urllib.parse import urlencode
from config import Config
from error_handlers import with_ai_error_handling
from logger_config import get_logger

logger = get_logger('linkedin_publisher')

def get_linkedin_credentials():
    client_id = Config.LINKEDIN_CLIENT_ID
    client_secret = Config.LINKEDIN_CLIENT_SECRET
    redirect_uri = 'http://localhost:5000/auth/linkedin/callback'
    scope = 'openid profile email w_member_social'
    return client_id, client_secret, redirect_uri, scope

def create_linkedin_session(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    return headers

def get_user_profile_v2(access_token):
    headers = create_linkedin_session(access_token)
    response = requests.get('https://api.linkedin.com/v2/userinfo', headers=headers)
    
    logger.info(f"Profile API Response Status: {response.status_code}")
    
    if response.status_code == 200:
        user_data = response.json()
        user_id = user_data.get('sub')
        if user_id:
            logger.info(f"Retrieved LinkedIn profile for user: {user_id}")
            return user_id
        else:
            logger.error("User ID not found in profile response")
            return None
    else:
        logger.error(f"Profile API failed: {response.status_code} - {response.text}")
        return None

def upload_image_to_linkedin_v2(access_token, user_id, image_path):
    try:
        headers = create_linkedin_session(access_token)
        register_url = 'https://api.linkedin.com/v2/assets?action=registerUpload'
        
        register_payload = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": f"urn:li:person:{user_id}",
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }]
            }
        }
        
        register_response = requests.post(register_url, headers=headers, json=register_payload)
        
        if register_response.status_code != 200:
            logger.error(f"Image register failed: {register_response.status_code} - {register_response.text}")
            return None
        
        upload_data = register_response.json()
        upload_url = upload_data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        asset_id = upload_data['value']['asset']
        
        with open(image_path, 'rb') as image_file:
            upload_response = requests.put(upload_url, data=image_file)
            if upload_response.status_code != 201:
                logger.error(f"Image upload failed: {upload_response.status_code}")
                return None
        
        logger.info(f"Image uploaded successfully: {asset_id}")
        return asset_id
    except Exception as error:
        logger.error(f"Image upload error: {str(error)}")
        return None

def create_post_payload(author_id, post_content):
    payload = {
        "author": f"urn:li:person:{author_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_content},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    return payload

def add_image_to_post_payload(payload, asset_id):
    payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
    payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
        "status": "READY",
        "description": {"text": "Generated image for post"},
        "media": asset_id,
        "title": {"text": "Social Media Post"}
    }]
    return payload

def submit_post_to_linkedin(access_token, payload):
    headers = create_linkedin_session(access_token)
    response = requests.post('https://api.linkedin.com/v2/ugcPosts', headers=headers, json=payload)
    return response.json(), response.status_code

def validate_post_creation(result, status_code):
    if status_code == 201 and 'id' in result:
        post_id = result['id']
        logger.info(f"LinkedIn post created successfully: {post_id}")
        return post_id
    else:
        logger.error(f"Post creation failed: Status {status_code}, Response: {result}")
        raise Exception(f"LinkedIn posting failed: {status_code}")

@with_ai_error_handling('linkedin_post_creation')
def create_linkedin_post(access_token, content, image_path=None):
    user_id = get_user_profile_v2(access_token)
    
    if not user_id:
        raise Exception("Failed to get LinkedIn user profile")
    
    payload = create_post_payload(user_id, content)
    
    if image_path:
        asset_id = upload_image_to_linkedin_v2(access_token, user_id, image_path)
        if asset_id:
            payload = add_image_to_post_payload(payload, asset_id)
        else:
            logger.warning("Image upload failed, posting without image")
    
    result, status_code = submit_post_to_linkedin(access_token, payload)
    post_id = validate_post_creation(result, status_code)
    return post_id

def get_linkedin_auth_url():
    client_id, _, redirect_uri, scope = get_linkedin_credentials()
    params = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': scope,
        'state': 'linkedin_auth'
    }
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"
    return auth_url

def exchange_code_for_token(code):
    client_id, client_secret, redirect_uri, _ = get_linkedin_credentials()
    
    token_payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    response = requests.post('https://www.linkedin.com/oauth/v2/accessToken', data=token_payload)
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access_token')
        if access_token:
            logger.info("LinkedIn access token obtained successfully")
            return access_token
        else:
            logger.error("Access token not found in response")
            raise Exception("LinkedIn token exchange failed: No access token")
    else:
        logger.error(f"Failed to get LinkedIn access token: {response.status_code} - {response.text}")
        raise Exception(f"LinkedIn token exchange failed: {response.status_code}")
