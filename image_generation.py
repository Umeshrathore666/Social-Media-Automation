from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os
import uuid
from datetime import datetime
from config import Config, get_upload_folder
from error_handlers import with_ai_error_handling
from logger_config import get_logger

logger = get_logger('image_generation')

def ensure_upload_directory():
    upload_dir = get_upload_folder()
    logger.info(f"Using upload directory: {upload_dir}")
    return upload_dir

def create_genai_client():
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        raise ValueError("Gemini API key not found in configuration")
    client = genai.Client(api_key=api_key)
    logger.info("Gemini client created successfully")
    return client

def generate_content_config():
    config = types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE']
    )
    return config

def create_image_prompt(content, platform):
    platform_styles = {
        'LinkedIn': 'professional, business-focused, clean and modern style',
        'Twitter': 'engaging, dynamic, social media optimized',
        'Instagram': 'visually appealing, vibrant colors, Instagram-style',
        'Facebook': 'friendly, approachable, social media friendly'
    }
    
    style = platform_styles.get(platform, 'professional and engaging')
    prompt = f"Create a high-quality image for a {platform} social media post about: {content[:200]}. Style: {style}, suitable for social media sharing"
    
    return prompt

def generate_unique_filename():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"generated_{timestamp}_{unique_id}.png"
    return filename

def send_generation_request(client, prompt, config):
    logger.info(f"Sending image generation request with prompt: {prompt[:100]}...")
    response = client.models.generate_content(
        model="gemini-2.0-flash-preview-image-generation",
        contents=prompt,
        config=config
    )
    logger.info("Image generation request completed")
    return response

def save_generated_image(image_data, filename):
    upload_dir = ensure_upload_directory()
    file_path = os.path.join(upload_dir, filename)
    
    image = Image.open(BytesIO(image_data))
    image.save(file_path, 'PNG', optimize=True, quality=85)
    logger.info(f"Image saved successfully: {filename}")
    return file_path

def process_generation_response(response, filename):
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            file_path = save_generated_image(part.inline_data.data, filename)
            relative_path = f"/static/generated_images/{filename}"
            logger.info(f"Image processed successfully: {relative_path}")
            return relative_path
        elif part.text is not None:
            logger.info(f"Generated text response: {part.text[:100]}...")
    
    raise Exception("No image data found in generation response")

def generate_image_for_post(content, platform='LinkedIn'):
    logger.info(f"Starting image generation for {platform} post")
    
    client = create_genai_client()
    config = generate_content_config()
    prompt = create_image_prompt(content, platform)
    filename = generate_unique_filename()
    
    response = send_generation_request(client, prompt, config)
    image_url = process_generation_response(response, filename)
    
    logger.info("Image generation completed successfully")
    return image_url

def cleanup_old_images():
    upload_dir = get_upload_folder()
    current_time = datetime.now()
    files_removed = 0
    
    for filename in os.listdir(upload_dir):
        file_path = os.path.join(upload_dir, filename)
        if os.path.isfile(file_path):
            file_age = datetime.fromtimestamp(os.path.getctime(file_path))
            age_days = (current_time - file_age).days
            
            if age_days > 7:
                os.remove(file_path)
                files_removed += 1
    
    if files_removed > 0:
        logger.info(f"Cleaned up {files_removed} old generated images")