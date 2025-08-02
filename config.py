"""
Configuration module for Discord Todo Bot.

Handles environment variables and configuration settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Discord Bot Token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Data directory for persistent storage
DATA_DIR = os.getenv('DATA_DIR', '/opt/render/project/src/data') 