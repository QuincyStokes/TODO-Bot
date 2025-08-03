#!/usr/bin/env python3
"""
Startup script for Discord Todo Bot with enhanced error handling and debugging.
"""

# Import audioop patch first to prevent import errors
import patch_audioop

import os
import sys
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('startup.log')
    ]
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set."""
    logger.info("Checking environment variables...")
    
    required_vars = ['DISCORD_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def check_data_directory():
    """Check if data directory exists and is writable."""
    logger.info("Checking data directory...")
    
    data_dir = os.getenv('DATA_DIR', '/opt/render/project/src/data')
    data_path = Path(data_dir)
    
    try:
        data_path.mkdir(parents=True, exist_ok=True)
        # Test write access
        test_file = data_path / 'test.txt'
        test_file.write_text('test')
        test_file.unlink()
        logger.info(f"✅ Data directory is writable: {data_dir}")
        return True
    except Exception as e:
        logger.error(f"❌ Data directory error: {e}")
        return False

def main():
    """Main startup function."""
    logger.info("🚀 Starting Discord Todo Bot...")
    
    # Check environment
    if not check_environment():
        logger.error("Environment check failed. Exiting.")
        sys.exit(1)
    
    # Check data directory
    if not check_data_directory():
        logger.error("Data directory check failed. Exiting.")
        sys.exit(1)
    
    # Import and run bot
    try:
        logger.info("Importing bot module...")
        from bot import main as run_bot
        logger.info("Starting bot...")
        run_bot()
    except ImportError as e:
        logger.error(f"Failed to import bot module: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during startup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 