import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///social_automation.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or 'AIzaSyBuVLSP48uZ7bUxY_WuMNIZTGsW_TENAts'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'generated_images')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

def get_upload_folder():
    upload_folder = Config.UPLOAD_FOLDER
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    return upload_folder