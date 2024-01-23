import logging
import os
from pathlib import Path

WRK_DIR = Path(__file__).resolve().parents[1]
log_file_path = os.path.join(WRK_DIR, "logs", "automation.log")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(log_file_path)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
file_handler.setFormatter(file_formatter)
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)
