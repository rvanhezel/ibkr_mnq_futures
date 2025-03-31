import os
from datetime import datetime
import logging


class Logger:
    
    def __init__(self):
        output_path = os.path.join(os.getcwd(), "output")
        timestmp = datetime.now()
        filename_timestmp = os.path.join(output_path, f"Logger_{timestmp.strftime('%d%m%Y')}.log")

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        logging.basicConfig(
            filename=filename_timestmp,
            format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
            datefmt='%d/%m/%Y %H:%M:%S',
            filemode='w',
            level=logging.DEBUG)
        
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(console_handler)
        
        logging.info("Logger initialized")
