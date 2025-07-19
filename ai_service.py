import google.generativeai as genai
import requests
import json
from config import Config
from error_handlers import with_ai_error_handling
from logger_config import get_logger

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

@with_ai_error_handling('image_query_generation')
def generate_image_search_query(content):
    model = genai.GenerativeModel('gemini-2.5-pro')
    prompt = f"Based on this social media post content, suggest 3-5 keywords for finding a relevant stock image: {content[:200]}"
    
    logger.info("Generating image search query")
    response = model.generate_content(prompt)
    return response.text.replace(',', ' ').replace('\n', ' ')

def fetch_relevant_image(content):
    try:
        search_query = generate_image_search_query(content)
        logger.info(f"Fetching image for query: {search_query}")
        
        api_url = f"https://api.unsplash.com/search/photos"
        params = {
            'query': search_query,
            'per_page': 1,
            'orientation': 'landscape'
        }
        headers = {
            'Authorization': 'Client-ID YOUR_UNSPLASH_ACCESS_KEY'
        }
        
        response = requests.get(api_url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                image_url = data['results'][0]['urls']['regular']
                logger.info("Image fetched successfully from Unsplash")
                return image_url
    except Exception as error:
        logger.warning(f"Failed to fetch image from Unsplash: {str(error)}")
    
    placeholder_url = "https://via.placeholder.com/800x400/4CAF50/white?text=Social+Media+Post"
    logger.info("Using placeholder image")
    return placeholder_url

@with_ai_error_handling('complete_post_generation')
def generate_complete_post(platform, topic):
    logger.info(f"Starting complete post generation for {platform} about {topic}")
    content = generate_post_content(platform, topic)
    image_url = fetch_relevant_image(content)
    
    result = {
        'content': content,
        'image_url': image_url,
        'platform': platform,
        'topic': topic
    }
    
    logger.info("Complete post generation finished successfully")
    return result