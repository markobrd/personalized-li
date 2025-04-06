#!/usr/bin/env python3
"""
LinkedIn Scraper Demo
---------------------
This script demonstrates how to use the improved LinkedIn scraper.
"""

import asyncio
import argparse
import yaml
import logging
from pathlib import Path
from typing import List

# Import the scraper module
from linkedin_scraper import LinkedInScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper_demo.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "credentials": {
        "username": "",
        "password": ""
    },
    "urls": {
        "login_url": "https://www.linkedin.com/feed/",
        "fetch_url": "https://www.linkedin.com/login"
    },
    "settings": {
        "timeout": 30
    },
    "usernames": [],
    "topics": ["AI", "Machine Learning", "Data Science", "Business solutions"],
    "blacklist": [],
    "scrape_feed": True,
    "scrape_comments": True,
    "scrape_reactions": True,
    "max_feed_posts": 20,
    "max_user_posts": 10,
    "max_comments": 5,
    "max_reactions": 5,
    "posts_to_load": 5,
    "PORT": 5000
}


def create_default_config() -> None:
    """Create a default configuration file if it doesn't exist."""
    config_file = Path("config.yaml")
    
    if not config_file.exists():
        logger.info("Creating default configuration file")
        
        with open(config_file, 'w') as f:
            yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False)
            
        logger.info(f"Default configuration created at {config_file.absolute()}")
        logger.info("Please update with your LinkedIn credentials before running")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="LinkedIn Profile Scraper")
    
    parser.add_argument(
        "--usernames", 
        nargs="+", 
        help="LinkedIn usernames to scrape (space-separated)"
    )
    
    parser.add_argument(
        "--config", 
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the browser in headless mode"
    )
    
    return parser.parse_args()


async def run_scraper(usernames: List[str] = None, config_file: str = "config.yaml", headless: bool = False):
    """
    Run the LinkedIn scraper with the given parameters.
    
    Args:
        usernames: List of LinkedIn usernames to scrape
        config_file: Path to the configuration file
        headless: Whether to run the browser in headless mode
    """
    try:
        # Ensure config file exists
        if not Path(config_file).exists():
            create_default_config()
            logger.warning(f"Configuration file {config_file} created, please update it with your credentials")
            return
            
        # Load configuration
        with open(config_file) as f:
            config = yaml.safe_load(f)
            
        # Update with command line arguments if provided
        if usernames:
            config['usernames'] = usernames
            
        # Validate configuration
        if not config.get('credentials', {}).get('username') or not config.get('credentials', {}).get('password'):
            logger.error("LinkedIn credentials not configured. Please update the config file.")
            return
            
        if not config.get('usernames'):
            logger.warning("No usernames provided. Please specify usernames in config or command line.")
            return
            
        # Initialize and run the scraper
        scraper = LinkedInScraper(config, headless=headless)
        await scraper.run(config.get('usernames'))
        
    except Exception as e:
        logger.error(f"Error running scraper: {e}")


if __name__ == "__main__":
    # Parse command-line arguments
    args = parse_args()
    
    # Run the scraper with the provided arguments
    asyncio.run(run_scraper(
        usernames=args.usernames,
        config_file=args.config,
        headless=args.headless
    ))
