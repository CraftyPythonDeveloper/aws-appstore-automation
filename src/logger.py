import os
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler


WRK_DIR = Path(__file__).resolve().parents[1]
log_file_path = os.path.join(WRK_DIR, "src", "logs", "automation.log")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the logging level to DEBUG

# File Handler
file_handler = RotatingFileHandler(log_file_path, maxBytes=1024*1024*5, backupCount=5, encoding="utf-8")
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console Handler
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
console_handler.setFormatter(console_formatter)
console_handler.setLevel(logging.DEBUG)  # Set the console logging level to INFO
logger.addHandler(console_handler)
