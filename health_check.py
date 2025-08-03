#!/usr/bin/env python3
"""
Health check script for Discord Todo Bot.

This script can be used to monitor the bot's health and connection status.
"""

import requests
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_bot_health():
    """Check the bot's health status."""
    try:
        # Try to connect to the health endpoint
        response = requests.get('http://localhost:10000/health', timeout=10)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Bot is healthy: {data}")
            return True
        else:
            logger.error(f"Health check failed with status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Health check failed: {e}")
        return False

def main():
    """Main function to run health checks."""
    logger.info("Starting bot health check...")
    
    while True:
        if check_bot_health():
            logger.info("✅ Bot is running normally")
        else:
            logger.warning("⚠️ Bot health check failed")
        
        # Wait 5 minutes before next check
        time.sleep(300)

if __name__ == "__main__":
    main() 