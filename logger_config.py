import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_application_logger():
    log_directory = 'logs'
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
    
    log_filename = os.path.join(log_directory, 'social_automation.log')
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    file_handler = RotatingFileHandler(
        log_filename, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    
    logger = logging.getLogger('social_automation')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name):
    return logging.getLogger(f'social_automation.{name}')