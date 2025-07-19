import logging
from functools import wraps
from flask import flash, redirect, url_for, request, jsonify
from flask_login import current_user

logger = logging.getLogger('social_automation.error_handler')

def log_user_action(action_type):
    user_id = getattr(current_user, 'id', 'anonymous')
    user_agent = request.headers.get('User-Agent', 'unknown')
    ip_address = request.remote_addr
    
    logger.info(f"User Action - ID: {user_id}, Action: {action_type}, IP: {ip_address}, UA: {user_agent}")

def handle_database_error(error, operation):
    error_message = f"Database error during {operation}: {str(error)}"
    logger.error(error_message)
    flash('A database error occurred. Please try again.', 'error')
    return error_message

def handle_ai_service_error(error, operation):
    error_message = f"AI service error during {operation}: {str(error)}"
    logger.error(error_message)
    flash('AI service is temporarily unavailable. Please try again.', 'error')
    return error_message

def handle_general_error(error, operation):
    error_message = f"Error during {operation}: {str(error)}"
    logger.error(error_message)
    flash('An unexpected error occurred. Please try again.', 'error')
    return error_message

def with_error_handling(operation_name, redirect_route='dashboard', return_json=False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                log_user_action(operation_name)
                result = func(*args, **kwargs)
                logger.info(f"Successfully completed {operation_name}")
                return result
            except Exception as error:
                error_message = handle_general_error(error, operation_name)
                
                if return_json:
                    return jsonify({'error': error_message}), 500
                
                return redirect(url_for(redirect_route))
        return wrapper
    return decorator

def with_database_error_handling(operation_name, redirect_route='dashboard'):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                log_user_action(operation_name)
                result = func(*args, **kwargs)
                logger.info(f"Database operation successful: {operation_name}")
                return result
            except Exception as error:
                handle_database_error(error, operation_name)
                return redirect(url_for(redirect_route))
        return wrapper
    return decorator

def with_ai_error_handling(operation_name, fallback_response=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                log_user_action(f"AI_{operation_name}")
                result = func(*args, **kwargs)
                logger.info(f"AI operation successful: {operation_name}")
                return result
            except Exception as error:
                handle_ai_service_error(error, operation_name)
                return fallback_response or {'content': 'Error generating content', 'image_url': ''}
        return wrapper
    return decorator