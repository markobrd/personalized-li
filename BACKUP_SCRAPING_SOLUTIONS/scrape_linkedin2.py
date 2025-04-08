import os
import json
import yaml
import datetime
import subprocess
import asyncio
from pathlib import Path
from typing import List, Dict, Set
import pickle
from asynciolimiter import Limiter

from selenium_driverless import webdriver
from selenium_driverless.types.by import By


from scrape_functions2 import *
import Gpt_check_topic


# ────────────────────────────────
# Configuration
# ────────────────────────────────
with open('config.yaml') as config_file:
    config = yaml.safe_load(config_file)

USERNAME = config['credentials']['username']
PASSWORD = config['credentials']['password']
LOGIN_URL = config['urls']['login_url']
FETCH_URL = config['urls']['fetch_url']
TIMEOUT = config['settings']['timeout']
APPROVED_TOPICS = config['topics']
BLACKLIST = config.get("blacklist", [])
PORT = 5000


# ────────────────────────────────
# Driver Setup
# ────────────────────────────────
def setup_driver(incognito: bool = False):
    chrome_options = webdriver.ChromeOptions()
    #user_profile_path = 'C:/Users/Uros/AppData/Local/Google/Chrome/User Data/Default'
    #chrome_options.add_argument(f'user-data-dir={user_profile_path}')
    if incognito:
        chrome_options.add_argument("--incognito")
    return chrome_options
async def check_login_status(driver):
    return 'login' in await driver.current_url

async def load_cookies(driver):
    if Path("cookies.pkl").exists():
        cookies = pickle.load(open("cookies.pkl", "rb"))
        if cookies:
            # print("cookie domain")
            for cookie in cookies:
                # print(cookie['domain'])
                await driver.add_cookie(cookie)
            await driver.refresh()
        return True
    return False

async def save_cookies(driver):
    pickle.dump(await driver.get_cookies(), open("cookies.pkl", "wb"))

async def login(driver):
    # Go to login page
    await driver.get(LOGIN_URL)
    # Try to load cookies

    if await load_cookies(driver) : return
    # Login if needed (don't forget two step verification, if it's set up)
    login_page = await check_login_status(driver)
    if login_page:
        username_field = await driver.find_element(By.ID, "username")
        password_field = await driver.find_element(By.ID, "password")
        button = await driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        await username_field.send_keys(USERNAME)
        await password_field.send_keys(PASSWORD)
        await button.click()

        await asyncio.sleep(3.0)
        await save_cookies(driver=driver)
        print("Login successful.")



# ────────────────────────────────
# Post-Processing
# ────────────────────────────────
async def process_posts(posts: List[Dict]) -> List[Dict]:
    tasks = [Gpt_check_topic.check_topic(post, idx) for idx, post in enumerate(posts) if 'post_text' in post]
    responses = await asyncio.gather(*tasks)
    return [res for res in responses if 'post_text' in res]


def save_to_json(posts: List[Dict]) -> List[Dict]:
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    file_path = f"JSON_DATA/posts_{today}.json"

    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            old_posts = json.load(f)
    else:
        old_posts = []

    with open(file_path, 'w') as f:
        json.dump(old_posts + posts, f, indent=4)

    return posts


# ────────────────────────────────
# Visited Post Keys
# ────────────────────────────────
def load_visited_posts() -> Set[str]:
    file_path = "visited_posts.json"
    keys = set()
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            existing = json.load(f)
            keys.update(post['key'] for post in existing)
    return keys


def save_visited_posts(keys: Set[str]) -> List[Dict[str, str]]:
    file_path = "visited_posts.json"
    data = [{'key': k} for k in keys]
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)
    return data


# ────────────────────────────────
# HTML & Flask Helpers
# ────────────────────────────────
def save_html(html_content: str):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    with open(f"saved_feeds/approved_posts_{today}.html", 'w') as f:
        f.write(html_content)


def start_flask_server():
    print("Starting Flask server...")
    subprocess.Popen(['python', 'flask_server.py'])
    print("Flask server started.")

# ────────────────────────────────
# Async Scraping Routine
# ────────────────────────────────

rate_limiter = Limiter(1/4)

async def start_coroutine(saved_keys:Set[str], name:str ="", extension:str=""):
    posts = []
    options = webdriver.ChromeOptions()
    await rate_limiter.wait()
    async with webdriver.Chrome(options=options) as driver:
        await login(driver)
        if not name == "":
            posts, saved_keys = await fetch_posts_person(driver, name, extension, saved_keys, BLACKLIST)
            #print(posts)
            links = await scrape_link_only(driver, posts, "./ul[1]/li")
        else:
            posts, saved_keys = await fetch_posts(driver, saved_keys, BLACKLIST)
            links = await scrape_link_only(driver, posts, "//*[@data-finite-scroll-hotkey-item]")
    return {'posts':posts}

async def main():
    print(f"Started at: {datetime.datetime.now()}")
    driver = setup_driver(incognito=False)
    try:
        #saved_keys = load_visited_posts()
        saved_keys = {''}
        extensions = ["all","comments","reactions"]
        # Scrape: all / comments / reactions / feed
        #await start_coroutine(saved_keys, "nishkambatta", "all")
        tasks = [start_coroutine(saved_keys, "nishkambatta", extension) for extension in extensions]
        #tasks+= [start_coroutine(saved_keys)]

        results = await asyncio.gather(*tasks)
        #all_approved = approved_feed + approved_all + approved_comments + approved_reactions
        #approved_feed = await process_posts(all_approved)
        #print(all_approved)
        #save_to_json(all_approved)
        #save_visited_posts(saved_keys)

    finally:
        # Optional: await driver.quit()
        print(f"Finished at: {datetime.datetime.now()}")


if __name__ == "__main__":
    asyncio.run(main())