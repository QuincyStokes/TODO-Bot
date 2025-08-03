"""
Configuration for Discord Todo Bot
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Discord Bot Token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Data storage configuration
DATA_DIR = os.getenv('DATA_DIR', '/opt/render/project/src/data')

# Database configuration
USE_DATABASE = os.getenv('USE_DATABASE', 'true').lower() == 'true'
DATABASE_PATH = os.path.join(DATA_DIR, 'todo_bot.db') if USE_DATABASE else None

# Storage fallback configuration
JSON_FALLBACK_PATH = os.path.join(DATA_DIR, 'todo_lists.json')

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'bot.log') 