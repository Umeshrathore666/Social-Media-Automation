import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or 'sqlite:///social_automation.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') 
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'generated_images')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    LINKEDIN_CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID') or 'your-linkedin-client-id'
    LINKEDIN_CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET') or 'your-linkedin-client-secret'
    
    TWITTER_API_KEY = os.getenv('TWITTER_API_KEY') or 'your-twitter-api-key'
    TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET') or 'your-twitter-api-secret'
    TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN') or 'your-twitter-access-token'
    TWITTER_ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET') or 'your-twitter-access-token-secret'
    
    FACEBOOK_APP_ID = os.getenv('FACEBOOK_APP_ID') or 'your-facebook-app-id'
    FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET') or 'your-facebook-app-secret'
    
    INSTAGRAM_ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN') or 'your-instagram-access-token'

def get_upload_folder():
    upload_folder = Config.UPLOAD_FOLDER
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    return upload_folder