import asyncio
import json
from playwright.async_api import async_playwright
from asynciolimiter import Limiter
from scrape_functions import fetch_posts, fetch_posts_person, scrape_link_only
import datetime
import os
import yaml
import subprocess
import Gpt_check_topic


# Load the config
with open('config.yaml') as config_file:
    config = yaml.safe_load(config_file)

# Configuration
USERNAME = config['credentials']['username']
PASSWORD = config['credentials']['password']
TIMEOUT = config['settings']['timeout']
APPROVED_TOPICS = config['topics']  # Replace with your approved topics
STALKLIST = config['stalklist']
PORT = 5000

#LOGIN AND COOKIES SETUP

async def login_and_get_cookies(page, email, password):
    await page.goto('https://www.linkedin.com/login', timeout=60000)
    await load_cookies(page)
    if not page.url.startswith('https://www.linkedin.com/feed'):
        elem = page.locator("#username")
        await elem.fill(email)
        elem = page.locator("#password")
        await elem.fill(password)
        await page.click('.btn__primary--large.from__button--floating')

    #await page.wait_for_load_state('networkidle')
    cookies = await page.context.cookies()
    print("Got cookies")
    with open(f'cookies{USERNAME}.json', 'w') as f:
        json.dump(cookies, f)
    print("Logged in and saved cookies.")

async def load_cookies(context):
    try:
        with open(f'cookies{USERNAME}.json', 'r') as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        print("Loaded cookies.")
        return True
    except FileNotFoundError:
        print("No saved cookies found.")
        return False

#SAVING AND LOADING POSTS

def save_to_json(posts):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    file_name = f"JSON_DATA/posts_{today}.json"
    old_posts = []
    if os.path.exists(file_name):
        with open(file_name, 'r') as file:
            old_posts = json.load(file)
    with open(file_name, 'w') as file:
        json.dump(posts+old_posts, file, indent=4)
    
    return posts

def load_visited_posts():
    file_name = "visited_posts.json"
    keys = {''}
    existing_keys =[]
    if os.path.exists(file_name):
        with open(file_name, 'r') as file:
            existing_keys = json.load(file)
    for key in existing_keys:
        keys.add(key['key'])
    return keys

def save_visited_posts(keys):
    new_keys = []
    file_name = "visited_posts.json"
    for key in keys:
        new_keys.append({'key':key})

    with open(file_name, 'w') as file:
        json.dump(new_keys, file, indent=4)

    return new_keys

#GPT PROCESSING 

def call_chatgpt_api(post_text):
    """response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"Determine if the following post is on an approved topic: {post_text}",
        max_tokens=10
    )
    return "approved" in response.choices[0].text.lower()"""
    return Gpt_check_topic.check_topic(post_text)

async def process_posts(posts):
    approved_posts = []

    tasks = [Gpt_check_topic.check_topic(posts[i], i) for i in range(len(posts)) if 'post_text' in posts[i]]
    responses = await asyncio.gather(*tasks)
    approved_posts = [response for response in responses if 'post_text' in response]
    return approved_posts

#SERVER START

def start_flask_server():
    print("Starting Flask server...")
    subprocess.Popen(['python', 'flask_server.py'])
    print("Flask server started.")    

#SCRAPING

rate_limiter = Limiter(1/3)
async def scrape_feed(browser, saved_keys, blacklist):
    context = await browser.new_context()
    page = await context.new_page()
    
    await load_cookies(context)
    await page.goto('https://www.linkedin.com/feed/', timeout=60000)
    if not page.url.startswith('https://www.linkedin.com/feed'):
        print("Cookies invalid, logging in...")
        await login_and_get_cookies(page, USERNAME, PASSWORD)  # Replace securely
        await page.goto('https://www.linkedin.com/feed/', timeout=60000)

    posts, saved_keys = await fetch_posts(page, saved_keys, blacklist)
    #links = await scrape_link_only(page, posts, "//*[@data-finite-scroll-hotkey-item]")
    await context.close()
    return posts, saved_keys


async def scrape_person(browser, person, extension, saved_keys, blacklist):
    await rate_limiter.wait()
    context = await browser.new_context()
    await load_cookies(context)


    page = await context.new_page()
    url = f'https://www.linkedin.com/in/{person}/recent-activity/{extension}'
    await page.goto(url, timeout=60000)
    posts, saved_keys = await fetch_posts_person(page, person, extension, saved_keys, blacklist)
    #links = await scrape_link_only(page, posts, "./ul[1]/li")
    await context.close()
    return {'posts':posts, 'ext':extension}

async def main():
    #saved_keys = load_visited_posts()
    saved_keys = set()
    blacklist = config['blacklist']

    extensions = config['extensions']

    async with async_playwright() as p:
        print(datetime.datetime.now())
        browser = await p.chromium.launch(headless=False)
        #posts, saved_keys = await scrape_feed(browser, saved_keys, blacklist)
        
        context = await browser.new_context()
        page = await context.new_page() 
        tasks = []

        for person in STALKLIST:
            tasks += [scrape_person(browser, person, extension, saved_keys, blacklist) for extension in extensions]
        results = await asyncio.gather(*tasks)
        out  = []
        visited = set()

        for result in results:
            for post in result['posts']:

                if (post['data_id']) and (not post['data_id'] in visited):
                    out.append(post)
                    visited.add(post['data_id'])

        #out = posts + out
        out = await process_posts(out)
        save_to_json(out)
        await browser.close()
    print(datetime.datetime.now())
    start_flask_server()
if __name__ == "__main__":
    asyncio.run(main())
