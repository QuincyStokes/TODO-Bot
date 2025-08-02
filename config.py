import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')  # Optional: restrict to specific server

# Database Configuration (using JSON for simplicity)
TODO_FILE = 'todo_lists.json' 