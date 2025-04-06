"""
LinkedIn Profile Scraper
------------------------
An improved LinkedIn scraper that can fetch posts, comments, and reactions
from multiple user profiles in a more robust and maintainable way.
"""

import asyncio
import datetime
import json
import logging
import os
import pickle
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import yaml
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (NoSuchElementException,
                                        StaleElementReferenceException,
                                        TimeoutException)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
import Gpt_check_topic

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("linkedin_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load configuration
try:
    with open('config.yaml') as config_file:
        CONFIG = yaml.safe_load(config_file)
except Exception as e:
    logger.error(f"Failed to load config: {e}")
    CONFIG = {}

class LinkedInScraper:
    """A class to handle LinkedIn scraping operations."""
    
    def __init__(self, config: Dict = None, headless: bool = False):
        """
        Initialize the LinkedIn scraper.
        
        Args:
            config: Configuration dictionary with credentials and settings
            headless: Whether to run the browser in headless mode
        """
        self.config = config or CONFIG
        self.headless = headless
        self.driver = None
        self.saved_keys = set()
        self.data_dir = Path("JSON_DATA")
        self.data_dir.mkdir(exist_ok=True)
        
        # Configuration values
        self.username = self.config.get('credentials', {}).get('username', '')
        self.password = self.config.get('credentials', {}).get('password', '')
        self.login_url = self.config.get('urls', {}).get('login_url', 'https://www.linkedin.com/feed/')
        self.timeout = self.config.get('settings', {}).get('timeout', 30)
        self.blacklist = self.config.get('blacklist', [])
        
        # Load previous visited posts
        self.load_visited_posts()

    def setup_driver(self) -> None:
        """Initialize and configure the Chrome WebDriver with user profile for persistent login."""
        chrome_options = Options()
        
        # Add user profile if specified in config or use default path by platform
        user_profile_path = self.config.get('chrome_profile_path', None)
        
        if not user_profile_path:
            # Determine default profile path based on platform
            import platform
            system = platform.system()
            home_dir = os.path.expanduser("~")
            
            if system == "Windows":
                user_profile_path = os.path.join(home_dir, "AppData", "Local", "Google", "Chrome", "User Data")
            elif system == "Darwin":  # macOS
                user_profile_path = os.path.join(home_dir, "Library", "Application Support", "Google", "Chrome")
            elif system == "Linux":
                user_profile_path = os.path.join(home_dir, ".config", "google-chrome")
            
            logger.info(f"Using default Chrome profile path for {system}: {user_profile_path}")
        
        # Check if the profile path exists
        if user_profile_path and os.path.exists(user_profile_path):
            chrome_options.add_argument(f"--user-data-dir={user_profile_path}")
            logger.info(f"Using Chrome profile at: {user_profile_path}")
            
            # Specify profile name if available
            profile_name = self.config.get('chrome_profile_name', 'Default')
            chrome_options.add_argument(f"--profile-directory={profile_name}")
            logger.info(f"Using Chrome profile: {profile_name}")
        else:
            logger.warning(f"Chrome profile path not found: {user_profile_path}")
            logger.info("Continuing without user profile")
        
        # Set headless mode if requested
        if self.headless:
            chrome_options.add_argument("--headless=new")  # New headless implementation in Chrome
            chrome_options.add_argument("--window-size=1920,1080")
            logger.info("Running in headless mode")
        
        # Add additional Chrome options for better stability
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Add user agent to avoid detection
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
        
        # Add preferences to avoid save password prompts
        chrome_prefs = {
            "profile.password_manager_enabled": False,
            "credentials_enable_service": False,
            "profile.default_content_setting_values.notifications": 2  # Block notifications
        }
        chrome_options.add_experimental_option("prefs", chrome_prefs)
        
        # Avoid detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Set up the WebDriver
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
            
            # Execute CDP commands to hide automation
            self.driver.execute_cdp_cmd("Network.enable", {})
            self.driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"}})
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """
            })
            
            logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            raise

    def close_driver(self) -> None:
        """Close the WebDriver if it's open."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None

    def save_cookies(self) -> None:
        """Save the current browser cookies to a file."""
        if not self.driver:
            logger.error("Cannot save cookies: WebDriver not initialized")
            return
            
        try:
            cookies = self.driver.get_cookies()
            if not cookies:
                logger.warning("No cookies found to save")
                return
                
            with open("cookies.pkl", "wb") as f:
                pickle.dump(cookies, f)
            logger.info(f"Saved {len(cookies)} cookies to file")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")

    def load_cookies(self) -> bool:
        """
        Load cookies from file and add them to the browser.
        
        Returns:
            bool: True if cookies were loaded successfully, False otherwise
        """
        if not self.driver:
            logger.error("Cannot load cookies: WebDriver not initialized")
            return False
            
        cookie_path = Path("cookies.pkl")
        if not cookie_path.exists():
            logger.info("No cookies file found")
            return False
            
        try:
            # First, ensure we're on a linkedin.com domain before adding cookies
            current_url = self.driver.current_url
            if "linkedin.com" not in current_url:
                self.driver.get("https://www.linkedin.com/")
                time.sleep(2)  # Wait for page to load
                
            with open(cookie_path, "rb") as f:
                cookies = pickle.load(f)
                    
            if not cookies:
                logger.info("No cookies found in file")
                return False
                
            # Add each cookie to the browser
            cookie_count = 0
            for cookie in cookies:
                try:
                    # Some cookie attributes might cause issues, remove them
                    if 'expiry' in cookie:
                        cookie['expiry'] = int(cookie['expiry'])
                    
                    # Skip cookies with invalid domains
                    if not cookie.get('domain'):
                        continue
                        
                    self.driver.add_cookie(cookie)
                    cookie_count += 1
                except Exception as e:
                    logger.debug(f"Failed to add cookie: {e}")
                        
            # Refresh the page to apply cookies
            self.driver.refresh()
            time.sleep(3)  # Give time for the cookies to take effect
            
            logger.info(f"Loaded {cookie_count} cookies successfully")
            
            # Verify login status after loading cookies
            if self.check_login_status():
                logger.info("Successfully logged in with cookies")
                return True
            else:
                logger.warning("Loaded cookies but not logged in")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return False

    def check_login_status(self) -> bool:
        """
        Check if we are currently logged in to LinkedIn.
        
        Returns:
            bool: True if logged in, False otherwise
        """
        if not self.driver:
            return False
            
        try:
            # Check for login page indicators
            if 'login' in self.driver.current_url or 'signup' in self.driver.current_url:
                logger.debug("On login/signup page - not logged in")
                return False
                
            # Look for elements that appear only when logged in
            try:
                # Try multiple selectors that indicate logged-in state
                nav_selectors = [
                    (By.ID, "global-nav"),
                    (By.CLASS_NAME, "global-nav__me"),
                    (By.XPATH, "//a[contains(@href, '/feed')]"),
                    (By.XPATH, "//div[contains(@class, 'feed-identity-module')]")
                ]
                
                for by, selector in nav_selectors:
                    try:
                        element = self.driver.find_element(by, selector)
                        if element.is_displayed():
                            logger.debug(f"Found logged-in indicator: {selector}")
                            return True
                    except NoSuchElementException:
                        continue
                
                # Check for elements that appear only when not logged in
                login_selectors = [
                    (By.ID, "session_key"),
                    (By.ID, "session_password"),
                    (By.XPATH, "//button[contains(@class, 'sign-in-form__submit-button')]")
                ]
                
                for by, selector in login_selectors:
                    try:
                        element = self.driver.find_element(by, selector)
                        if element.is_displayed():
                            logger.debug(f"Found logged-out indicator: {selector}")
                            return False
                    except NoSuchElementException:
                        continue
                    
                logger.debug("Could not definitively determine login status")
                return False
                    
            except Exception as e:
                logger.error(f"Error checking for logged-in elements: {e}")
                return False
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return False

    def login(self) -> bool:
        """
        Log in to LinkedIn using the credentials from the config.
        
        Returns:
            bool: True if login was successful, False otherwise
        """
        if not self.driver:
            logger.error("Cannot login: WebDriver not initialized")
            return False
            
        if not self.username or not self.password:
            logger.error("Cannot login: Username or password not provided")
            return False
            
        try:
            # Navigate to login page if not already there
            current_url = self.driver.current_url
            if "linkedin.com" not in current_url:
                logger.info("Navigating to LinkedIn")
                self.driver.get("https://www.linkedin.com/")
                time.sleep(2)  # Wait for page to load
            
            # Try to use cookies first
            if self.load_cookies():
                if self.check_login_status():
                    logger.info("Successfully logged in using saved cookies")
                    return True
                else:
                    logger.info("Cookies loaded but not logged in, will try manual login")
            
            # Navigate to login page
            logger.info("Navigating to login page")
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)  # Wait for page to load
            
            # Find username and password fields
            try:
                username_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
                password_field = self.driver.find_element(By.ID, "password")
            except (NoSuchElementException, TimeoutException) as e:
                logger.error(f"Login form elements not found: {e}")
                # Try alternative login form
                try:
                    username_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.ID, "session_key"))
                    )
                    password_field = self.driver.find_element(By.ID, "session_password")
                except (NoSuchElementException, TimeoutException) as e:
                    logger.error(f"Alternative login form elements not found: {e}")
                    return False
            
            # Clear fields and enter credentials
            logger.info("Entering login credentials")
            username_field.clear()
            username_field.send_keys(self.username)
            time.sleep(0.5)  # Small delay between fields
            password_field.clear()
            password_field.send_keys(self.password)
            time.sleep(0.5)  # Small delay before submission
            
            # Submit the form
            try:
                # Try the sign-in button if available
                try:
                    sign_in_button = self.driver.find_element(By.XPATH, "//button[contains(@class, 'btn__primary--large') or contains(@class, 'sign-in-form__submit-button')]")
                    sign_in_button.click()
                except NoSuchElementException:
                    # Fall back to pressing Enter
                    password_field.send_keys(Keys.RETURN)
                    
                logger.info("Login form submitted")
            except Exception as e:
                logger.error(f"Error submitting login form: {e}")
                return False
            
            # Wait for login to complete
            try:
                # Wait for redirection to feed or similar page
                WebDriverWait(self.driver, self.timeout).until(
                    lambda driver: "feed" in driver.current_url 
                                or "mynetwork" in driver.current_url
                                or "checkpoint" in driver.current_url  # Handle security checkpoints
                )
                
                # Check if we're at a security checkpoint
                if "checkpoint" in self.driver.current_url:
                    logger.warning("LinkedIn security checkpoint detected. Manual intervention required.")
                    
                    # Wait longer for manual intervention
                    extended_timeout = self.timeout * 2
                    logger.info(f"Waiting {extended_timeout} seconds for manual security verification...")
                    
                    # Wait for redirect after security verification
                    WebDriverWait(self.driver, extended_timeout).until(
                        lambda driver: "feed" in driver.current_url or "mynetwork" in driver.current_url
                    )
                
                # Verify login status
                if self.check_login_status():
                    logger.info("Login successful")
                    
                    # Save cookies for future use
                    self.save_cookies()
                    return True
                else:
                    logger.error("Login redirect occurred but still not logged in")
                    return False
                    
            except TimeoutException:
                logger.error("Login timed out or failed")
                
                # Check if we're still on a login page
                if ("login" in self.driver.current_url or 
                    "checkpoint" in self.driver.current_url or 
                    "add-phone" in self.driver.current_url):
                    logger.error("Still on login/verification page. Manual intervention may be required.")
                
                return False
                
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def load_visited_posts(self) -> None:
        """Load the list of visited post IDs from a file."""
        file_path = Path("visited_posts.json")
        self.saved_keys = {''}  # Empty string as default
        
        if not file_path.exists():
            logger.info("No visited posts file found, starting fresh")
            return
            
        try:
            with open(file_path, 'r') as file:
                existing_keys = json.load(file)
                
            for key in existing_keys:
                self.saved_keys.add(key.get('key', ''))
                
            logger.info(f"Loaded {len(self.saved_keys)} visited post IDs")
        except Exception as e:
            logger.error(f"Failed to load visited posts: {e}")

    def save_visited_posts(self) -> None:
        """Save the current set of visited post IDs to a file."""
        new_keys = [{'key': key} for key in self.saved_keys if key]
        file_path = Path("visited_posts.json")
        
        try:
            with open(file_path, 'w') as file:
                json.dump(new_keys, file, indent=4)
                
            logger.info(f"Saved {len(new_keys)} visited post IDs")
        except Exception as e:
            logger.error(f"Failed to save visited posts: {e}")

    def save_to_json(self, posts: List[Dict]) -> None:
        """
        Save the given posts to a JSON file with today's date.
        
        Args:
            posts: List of post dictionaries to save
        """
        if not posts:
            logger.info("No posts to save")
            return
            
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        file_path = self.data_dir / f"posts_{today}.json"
        
        # Load existing posts if any
        existing_posts = []
        if file_path.exists():
            try:
                with open(file_path, 'r') as file:
                    existing_posts = json.load(file)
            except Exception as e:
                logger.error(f"Failed to load existing posts: {e}")
        
        # Combine with new posts and save
        try:
            with open(file_path, 'w') as file:
                json.dump(existing_posts + posts, file, indent=4)
                
            logger.info(f"Saved {len(posts)} posts to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save posts to JSON: {e}")

    def wait_for_element(self, by: By, value: str, timeout: int = None) -> Optional[webdriver.remote.webelement.WebElement]:
        """
        Wait for an element to be present in the DOM.
        
        Args:
            by: The locator strategy to use
            value: The locator value
            timeout: How long to wait for the element (seconds)
            
        Returns:
            The WebElement if found, None otherwise
        """
        if timeout is None:
            timeout = self.timeout
            
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except (TimeoutException, NoSuchElementException) as e:
            logger.warning(f"Element not found: {by}={value}, {e}")
            return None

    def scroll_page(self, pause_time: float = 1.0, scroll_count: int = 2) -> None:
        """
        Scroll the page to load more content.
        
        Args:
            pause_time: Time to pause between scrolls (seconds)
            scroll_count: Number of times to scroll
        """
        try:
            # Get current scroll height
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            for _ in range(scroll_count):
                # Scroll down halfway
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(pause_time)
                
                # Scroll down to bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(pause_time)
                
                # Calculate new scroll height and compare with last scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
        except Exception as e:
            logger.error(f"Error during scrolling: {e}")

    async def fetch_posts_feed(self, max_posts: int = 20) -> List[Dict]:
        """
        Fetch posts from the LinkedIn feed.
        
        Args:
            max_posts: Maximum number of posts to fetch
            
        Returns:
            List of post dictionaries
        """
        if not self.driver:
            logger.error("Cannot fetch posts: WebDriver not initialized")
            return []
            
        logger.info("Fetching posts from feed")
        posts = []
        
        try:
            # Navigate to feed
            self.driver.get('https://www.linkedin.com/feed/')
            
            # Scroll to load more content
            self.scroll_page(pause_time=1.5, scroll_count=3)
            
            # Wait for the feed content to load
            feed_content = self.wait_for_element(
                By.CLASS_NAME, 'scaffold-finite-scroll__content', 
                timeout=10
            )
            
            if not feed_content:
                logger.error("Feed content not found")
                return []
                
            # Parse the HTML content
            soup = BeautifulSoup(feed_content.get_attribute('innerHTML'), 'html.parser')
            
            # Process post elements
            post_count = 0
            for post_div in soup.select("[data-finite-scroll-hotkey-item]"):
                # Extract post data
                post_data = self._extract_post_data(post_div)
                if post_data and post_data.get('data_id') not in self.saved_keys:
                    post_count += 1
                    posts.append(post_data)
                    self.saved_keys.add(post_data.get('data_id', ''))
                    
                # Stop if we've reached the maximum number of posts
                if post_count >= max_posts:
                    break
                    
            logger.info(f"Found {len(posts)} new posts in feed")
            return posts
            
        except Exception as e:
            logger.error(f"Error fetching feed posts: {e}")
            return []

    async def fetch_posts_person(self, username: str, activity_type: str = "all", max_posts: int = 10) -> List[Dict]:
        """
        Fetch posts from a specific user's activity.
        
        Args:
            username: LinkedIn username to fetch
            activity_type: Type of activity to fetch ("all", "comments", "reactions")
            max_posts: Maximum number of posts to fetch
            
        Returns:
            List of post dictionaries
        """
        if not self.driver:
            logger.error("Cannot fetch posts: WebDriver not initialized")
            return []
            
        logger.info(f"Fetching {activity_type} posts for user: {username}")
        posts = []
        
        try:
            # Validate activity type
            if activity_type not in ["all", "comments", "reactions"]:
                logger.warning(f"Invalid activity type: {activity_type}, using 'all'")
                activity_type = "all"
                
            # Navigate to user's activity page
            url = f'https://www.linkedin.com/in/{username}/recent-activity/{activity_type}'
            self.driver.get(url)
            
            # Scroll to load more content
            self.scroll_page(pause_time=1.5, scroll_count=3)
            
            # Wait for the content to load
            content_element = self.wait_for_element(
                By.CLASS_NAME, 'scaffold-finite-scroll__content', 
                timeout=10
            )
            
            if not content_element:
                logger.error(f"Content not found for {username}'s {activity_type}")
                return []
                
            # Find the UL containing the posts
            try:
                post_list = content_element.find_element(By.XPATH, './ul[1]')
                soup = BeautifulSoup(post_list.get_attribute('innerHTML'), 'html.parser')
            except NoSuchElementException:
                logger.error(f"Post list not found for {username}'s {activity_type}")
                return []
                
            # Process post elements
            post_count = 0
            for post_li in soup.find_all("li", recursive=False):
                # Extract post data
                post_data = self._extract_person_post_data(post_li, post_count)
                if post_data and post_data.get('data_id') not in self.saved_keys:
                    post_count += 1
                    posts.append(post_data)
                    self.saved_keys.add(post_data.get('data_id', ''))
                    
                # Stop if we've reached the maximum number of posts
                if post_count >= max_posts:
                    break
                    
            logger.info(f"Found {len(posts)} new posts for {username}'s {activity_type}")
            return posts
            
        except Exception as e:
            logger.error(f"Error fetching {activity_type} posts for {username}: {e}")
            return []

    def _extract_post_data(self, post_div: BeautifulSoup) -> Optional[Dict]:
        """
        Extract post data from a BeautifulSoup element in the feed.
        
        Args:
            post_div: BeautifulSoup element containing the post
            
        Returns:
            Dictionary with post data, or None if extraction failed
        """
        try:
            post_data = {}
            
            # Get post content
            post_content = post_div.find('div', class_='feed-shared-inline-show-more-text')
            if not post_content:
                return None
                
            # Generate a unique ID for the post
            data_id = post_content.get_text(strip=True)[:35]
            if not data_id or data_id in self.saved_keys:
                return None
                
            # Get profile information
            profile_container = post_div.find('div', class_='update-components-actor__container')
            if not profile_container:
                return None
                
            profile_link = profile_container.find('a')
            if not profile_link:
                return None
                
            # Check blacklist
            profile_href = profile_link.get('href', '')
            if profile_href:
                username_parts = profile_href.split("/")
                if len(username_parts) > 3 and username_parts[3] in self.blacklist:
                    return None
                if len(username_parts) > 4 and username_parts[4].split("?")[0] in self.blacklist:
                    return None
            
            # Post data
            post_data['data_id'] = data_id
            post_data['profile_link'] = profile_href
            
            # Get profile image
            img_wrapper = post_div.find('div', class_='ivm-view-attr__img-wrapper')
            if img_wrapper and img_wrapper.find('img'):
                post_data['img_link'] = img_wrapper.find('img').get('src', '')
            
            # Get user name
            name_element = post_div.find('span', class_='update-components-actor__title')
            if name_element and name_element.find('span'):
                name_text = name_element.find('span').get_text(strip=True)
                post_data['name'] = name_text[:len(name_text)//2]
            else:
                post_data['name'] = ""
            
            # Get rank information
            rank_element = post_div.find('span', class_='update-components-actor__supplementary-actor-info')
            if rank_element:
                rank_text = rank_element.get_text(strip=True)
                post_data['rank'] = rank_text[:len(rank_text)//2]
            else:
                post_data['rank'] = ""
            
            # Get description
            desc_element = post_div.find('span', class_='update-components-actor__description')
            if desc_element:
                desc_text = desc_element.get_text(strip=True)
                post_data['description'] = desc_text[:len(desc_text)//2]
            else:
                post_data['description'] = ""
            
            # Get post time
            time_element = post_div.find('span', class_='update-components-actor__sub-description')
            if time_element:
                post_data['time_posted'] = time_element.get_text(strip=True)
            else:
                post_data['time_posted'] = ""
            
            # Get post text
            if post_content:
                # Replace <br> tags with newlines
                for br in post_content.find_all('br'):
                    br.replace_with('\n')
                
                # Extract text without the "see more" text at the end
                post_data['post_text'] = post_content.text[:-9] if post_content.text.endswith('see more') else post_content.text
            
            return post_data
            
        except Exception as e:
            logger.error(f"Error extracting post data: {e}")
            return None

    def _extract_person_post_data(self, post_li: BeautifulSoup, index: int) -> Optional[Dict]:
        """
        Extract post data from a BeautifulSoup element in a person's activity.
        
        Args:
            post_li: BeautifulSoup element containing the post
            index: Index of the post for identification
            
        Returns:
            Dictionary with post data, or None if extraction failed
        """
        try:
            post_data = {}
            
            # Get post content
            content = post_li.find("span", class_="break-words tvm-parent-container")
            if not content:
                return None
                
            # Find post ID element
            post_id_elem = post_li.find_all('div', class_="feed-shared-update-v2")
            if not post_id_elem:
                return None
                
            # Generate a unique ID for the post
            data_id = content.text.strip()[:35]
            if not data_id or data_id in self.saved_keys:
                return None
                
            # Get profile information
            profile_container = post_li.find('div', class_='update-components-actor__container')
            if not profile_container:
                return None
                
            profile_link = profile_container.find('a')
            if not profile_link:
                return None
                
            # Check blacklist
            profile_href = profile_link.get('href', '')
            if profile_href:
                username_parts = profile_href.split("/")
                if len(username_parts) > 3 and username_parts[3] in self.blacklist:
                    return None
                if len(username_parts) > 4 and username_parts[4].split("?")[0] in self.blacklist:
                    return None
            
            # Post data
            post_data['id'] = index
            post_data['data_id'] = data_id
            post_data['profile_link'] = profile_href
            
            # Replace <br> tags with newlines in content
            for br in content.find_all('br'):
                br.replace_with('\n')
                
            # Extract text without the "see more" text at the end
            post_data['post_text'] = content.text[:-9] if content.text.endswith('see more') else content.text
            
            # Get profile image
            img_wrapper = post_li.find('div', class_='ivm-view-attr__img-wrapper')
            if img_wrapper and img_wrapper.find('img'):
                post_data['img_link'] = img_wrapper.find('img').get('src', '')
            
            # Get user name
            name_element = post_li.find('span', class_='update-components-actor__title')
            if name_element and name_element.find('span'):
                name_text = name_element.find('span').get_text(strip=True)
                post_data['name'] = name_text[:len(name_text)//2]
            else:
                post_data['name'] = ""
            
            # Get rank information
            rank_element = post_li.find('span', class_='update-components-actor__supplementary-actor-info')
            if rank_element:
                rank_text = rank_element.get_text(strip=True)
                post_data['rank'] = rank_text[:len(rank_text)//2]
            else:
                post_data['rank'] = ""
            
            # Get description
            desc_element = post_li.find('span', class_='update-components-actor__description')
            if desc_element:
                desc_text = desc_element.get_text(strip=True)
                post_data['description'] = desc_text[:len(desc_text)//2]
            else:
                post_data['description'] = ""
            
            # Get post time
            time_element = post_li.find('span', class_='update-components-actor__sub-description')
            if time_element:
                post_data['time_posted'] = time_element.get_text(strip=True)
            else:
                post_data['time_posted'] = ""
            
            return post_data
            
        except Exception as e:
            logger.error(f"Error extracting person post data: {e}")
            return None

    def scrape_post_links(self, posts: List[Dict], xpath: str) -> List[Dict]:
        """
        Scrape links for the given posts.
        
        Args:
            posts: List of post dictionaries
            xpath: XPath to locate the post elements
            
        Returns:
            Updated list of post dictionaries with links
        """
        if not self.driver or not posts:
            return posts
            
        logger.info(f"Scraping links for {len(posts)} posts")
        
        try:
            # Find the container with all posts
            elements = self.wait_for_element(By.CLASS_NAME, 'scaffold-finite-scroll__content')
            if not elements:
                logger.error("Post container not found")
                return posts
                
            # Find post elements using the provided XPath
            post_elements = elements.find_elements(By.XPATH, xpath)
            if not post_elements:
                logger.error(f"No post elements found with XPath: {xpath}")
                return posts
                
            # Click on menu buttons for all posts
            for post in posts:
                index = post.get('id', -1)
                if index < 0 or index >= len(post_elements):
                    continue
                    
                try:
                    # Find and click the dropdown menu
                    dropdown = post_elements[index].find_elements(By.CLASS_NAME, 'artdeco-dropdown')
                    if not dropdown:
                        continue
                        
                    menu_button = dropdown[0].find_element(By.XPATH, './button[1]')
                    if menu_button:
                        self.driver.execute_script("arguments[0].click();", menu_button)
                except (NoSuchElementException, StaleElementReferenceException, IndexError) as e:
                    logger.warning(f"Error clicking menu for post {index}: {e}")
            
            # Wait for menus to open
            time.sleep(1)
            self.driver.execute_script("window.focus();")
            
            # Get links for each post
            for post in posts:
                index = post.get('id', -1)
                if index < 0 or index >= len(post_elements):
                    continue
                    
                try:
                    # Find the 'Copy link' option
                    dropdown = post_elements[index].find_elements(By.CLASS_NAME, 'artdeco-dropdown')
                    if not dropdown:
                        continue
                        
                    copy_link_option = dropdown[0].find_element(
                        By.XPATH, './div[1]/div[1]/ul[1]/li[2]/div[1]'
                    )
                    
                    if copy_link_option:
                        # Click the option to copy the link
                        self.driver.execute_script("arguments[0].click();", copy_link_option)
                        
                        # Get the link from toast notification
                        link_element = self.wait_for_element(
                            By.CLASS_NAME, 'artdeco-toast-item__cta',
                            timeout=5
                        )
                        
                        if link_element:
                            post_link = link_element.get_attribute("href")
                            post['post_link'] = post_link
                except (NoSuchElementException, StaleElementReferenceException, IndexError) as e:
                    logger.warning(f"Error getting link for post {index}: {e}")
            
            logger.info(f"Scraped links for {sum(1 for p in posts if 'post_link' in p)} posts")
            return posts
            
        except Exception as e:
            logger.error(f"Error scraping post links: {e}")
            return posts

    async def run(self, usernames: List[str] = None) -> None:
        """
        Run the scraper for the given usernames.
        
        Args:
            usernames: List of usernames to scrape. If None, uses from config.
        """
        if usernames is None:
            usernames = self.config.get('usernames', [])
            
        if not usernames:
            logger.warning("No usernames provided for scraping")
            
        logger.info(f"Starting scrape for usernames: {usernames}")
        
        # Initialize WebDriver
        self.setup_driver()
        
        # Store all approved posts
        all_approved_posts = []
        
        try:
            # Login to LinkedIn
            if not self.check_login_status():
                if not self.login():
                    logger.error("Failed to login, aborting scrape")
                    return
            
            # Scrape main feed if requested
            if self.config.get('scrape_feed', False):
                feed_posts = await self.fetch_posts_feed(max_posts=self.config.get('max_feed_posts', 20))
                if feed_posts:
                    # Get links for the posts
                    feed_posts_with_links = self.scrape_post_links(
                        feed_posts, 
                        "//*[@data-finite-scroll-hotkey-item]"
                    )
                    
                    # Process posts to check topic relevance
                    approved_feed_posts = await self.process_posts(feed_posts_with_links)
                    all_approved_posts.extend(approved_feed_posts)
            
            # Scrape each username's activity
            for username in usernames:
                logger.info(f"Scraping activity for user: {username}")
                
                # Scrape "all" activity
                all_posts = await self.fetch_posts_person(
                    username, 
                    "all", 
                    max_posts=self.config.get('max_user_posts', 10)
                )
                
                if all_posts:
                    # Get links for the posts
                    all_posts_with_links = self.scrape_post_links(all_posts, "./ul[1]/li")
                    
                    # Process posts to check topic relevance
                    approved_all_posts = await self.process_posts(all_posts_with_links)
                    all_approved_posts.extend(approved_all_posts)
                
                # Scrape comments
                if self.config.get('scrape_comments', True):
                    comment_posts = await self.fetch_posts_person(
                        username, 
                        "comments", 
                        max_posts=self.config.get('max_comments', 5)
                    )
                    
                    if comment_posts:
                        # Get links for the posts
                        comment_posts_with_links = self.scrape_post_links(comment_posts, "./ul[1]/li")
                        
                        # Process posts to check topic relevance
                        approved_comment_posts = await self.process_posts(comment_posts_with_links)
                        all_approved_posts.extend(approved_comment_posts)
                
                # Scrape reactions
                if self.config.get('scrape_reactions', True):
                    reaction_posts = await self.fetch_posts_person(
                        username, 
                        "reactions", 
                        max_posts=self.config.get('max_reactions', 5)
                    )
                    
                    if reaction_posts:
                        # Get links for the posts
                        reaction_posts_with_links = self.scrape_post_links(reaction_posts, "./ul[1]/li")
                        
                        # Process posts to check topic relevance
                        approved_reaction_posts = await self.process_posts(reaction_posts_with_links)
                        all_approved_posts.extend(approved_reaction_posts)
                
                logger.info(f"Finished scraping activity for user: {username}")
            
            # Save all approved posts to JSON
            if all_approved_posts:
                self.save_to_json(all_approved_posts)
                logger.info(f"Saved {len(all_approved_posts)} approved posts")
            else:
                logger.info("No approved posts found")
            
            # Save the updated set of visited post IDs
            self.save_visited_posts()
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        finally:
            # Close the WebDriver
            self.close_driver()
            
        logger.info("Scraping completed")

    async def process_posts(self, posts: List[Dict]) -> List[Dict]:
        """
        Process posts to check if they're relevant to the approved topics.
        
        Args:
            posts: List of post dictionaries to process
            
        Returns:
            List of approved post dictionaries
        """
        if not posts:
            return []
            
        logger.info(f"Processing {len(posts)} posts for topic relevance")
        approved_posts = []
        
        try:
            # Create tasks for each post with the GPT checker
            tasks = [
                Gpt_check_topic.check_topic(post, i)
                for i, post in enumerate(posts)
                if 'post_text' in post
            ]
            
            # Execute the tasks concurrently
            if tasks:
                responses = await asyncio.gather(*tasks)
                
                # Filter out empty responses
                approved_posts = [response for response in responses if response and 'post_text' in response]
                
            logger.info(f"Found {len(approved_posts)} relevant posts out of {len(posts)}")
            return approved_posts
            
        except Exception as e:
            logger.error(f"Error processing posts: {e}")
            return []


async def main():
    """Main function to run the LinkedIn scraper."""
    start_time = datetime.datetime.now()
    logger.info(f"Starting LinkedIn scraper at {start_time}")
    
    try:
        # Load configuration
        with open('config.yaml') as config_file:
            config = yaml.safe_load(config_file)
        
        # Get usernames from config or command line
        usernames = config.get('usernames', [])
        
        # Initialize and run the scraper
        scraper = LinkedInScraper(config)
        await scraper.run(usernames)
        
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")
    finally:
        end_time = datetime.datetime.now()
        duration = end_time - start_time
        logger.info(f"LinkedIn scraper finished at {end_time} (Duration: {duration})")


if __name__ == "__main__":
    asyncio.run(main())