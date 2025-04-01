import os
from datetime import datetime
import logging


class Logger:
    
    def __init__(self, timestamp: str = None):
        output_path = os.path.join(os.getcwd(), "output")
        timestmp = timestamp if timestamp is not None else datetime.now()       
         
        filename_timestmp = os.path.join(output_path, f"Logger_{timestmp.strftime('%d%m%Y')}.log")

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        # Get the root logger
        logger = logging.getLogger()
        
        # Remove all existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Create new file handler
        file_handler = logging.FileHandler(filename_timestmp, mode='w')
        file_handler.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)
        
        # Set level
        logger.setLevel(logging.DEBUG)
        
        logging.info("Logger initialized")
