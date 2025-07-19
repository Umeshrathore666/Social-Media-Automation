import google.generativeai as genai
import requests
import json
from config import Config

genai.configure(api_key=Config.GEMINI_API_KEY)

def get_platform_prompt(platform, topic):
    prompts = {
        'LinkedIn': f"Create a professional LinkedIn post about {topic}. Make it engaging and business-focused with relevant hashtags.",
        'Twitter': f"Create a concise Twitter post about {topic}. Keep it under 280 characters with relevant hashtags.",
        'Instagram': f"Create an Instagram post about {topic}. Make it visually appealing with emojis and hashtags.",
        'Facebook': f"Create a Facebook post about {topic}. Make it engaging and conversational."
    }
    return prompts.get(platform, f"Create a social media post about {topic}")

def generate_post_content(platform, topic):
    model = genai.GenerativeModel('gemini-pro')
    prompt = get_platform_prompt(platform, topic)
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating content: {str(e)}"

def generate_image_search_query(content):
    model = genai.GenerativeModel('gemini-pro')
    prompt = f"Based on this social media post content, suggest 3-5 keywords for finding a relevant stock image: {content[:200]}"
    
    try:
        response = model.generate_content(prompt)
        return response.text.replace(',', ' ').replace('\n', ' ')
    except Exception as e:
        return "business professional stock image"

def fetch_relevant_image(content):
    search_query = generate_image_search_query(content)
    
    try:
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
                return data['results'][0]['urls']['regular']
    except Exception as e:
        pass
    
    return "https://via.placeholder.com/800x400/4CAF50/white?text=Social+Media+Post"

def generate_complete_post(platform, topic):
    content = generate_post_content(platform, topic)
    image_url = fetch_relevant_image(content)
    
    return {
        'content': content,
        'image_url': image_url,
        'platform': platform,
        'topic': topic
    }