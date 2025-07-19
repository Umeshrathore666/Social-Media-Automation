import google.generativeai as genai
from config import Config
from error_handlers import with_ai_error_handling
from logger_config import get_logger
from image_generation import generate_image_for_post

logger = get_logger('ai_service')
genai.configure(api_key=Config.GEMINI_API_KEY)

def get_platform_prompt(platform, topic):
    prompts = {
        'LinkedIn': f"Create a professional LinkedIn post about {topic}. Make it engaging and business-focused with relevant hashtags.",
        'Twitter': f"Create a concise Twitter post about {topic}. Keep it under 280 characters with relevant hashtags.",
        'Instagram': f"Create an Instagram post about {topic}. Make it visually appealing with emojis and hashtags.",
        'Facebook': f"Create a Facebook post about {topic}. Make it engaging and conversational."
    }
    return prompts.get(platform, f"Create a social media post about {topic}")

@with_ai_error_handling('content_generation')
def generate_post_content(platform, topic):
    model = genai.GenerativeModel('gemini-2.5-pro')
    prompt = get_platform_prompt(platform, topic)
    
    logger.info(f"Generating content for platform: {platform}, topic: {topic}")
    response = model.generate_content(prompt)
    logger.info("Content generated successfully")
    return response.text

def generate_ai_image_for_content(content, platform):
    logger.info(f"Generating AI image for {platform} content")
    image_url = generate_image_for_post(content, platform)
    logger.info("AI image generated successfully")
    return image_url

@with_ai_error_handling('complete_post_generation')
def generate_complete_post(platform, topic):
    logger.info(f"Starting complete post generation for {platform} about {topic}")
    content = generate_post_content(platform, topic)
    image_url = generate_ai_image_for_content(content, platform)
    
    result = {
        'content': content,
        'image_url': image_url,
        'platform': platform,
        'topic': topic
    }
    
    logger.info("Complete post generation finished successfully")
    return result