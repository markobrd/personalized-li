import asyncio
import json
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from asynciolimiter import Limiter
from scrape_functions import fetch_posts, fetch_posts_person, scrape_link_only
import datetime
import os
import yaml
import subprocess
import Gpt_check_topic
import aioconsole
from multiprocessing import Queue


# Load the config
with open('config.yaml') as config_file:
    config = yaml.safe_load(config_file)

# Configuration
TIMEOUT = config['settings']['timeout']
APPROVED_TOPICS = config['topics']  # Replace with your approved topics
STALKLIST = config['stalklist']
PORT = 5000

# LOGIN AND COOKIES SETUP


async def login_and_get_cookies(page, email, password, context):
    await load_cookies(context, email)
    await page.goto('https://www.linkedin.com/login', timeout=60000)
    await asyncio.sleep(3)

    # We have to login manually
    if not page.url.startswith('https://www.linkedin.com/feed'):
        print("Cookies are invalid, logging in")
        elem = page.locator("#username")
        await elem.fill(email)
        elem = page.locator("#password")
        await elem.fill(password)
        await page.click('.btn__primary--large.from__button--floating')
        await asyncio.sleep(3)
    else:
        print("Succesfully logged in")
        cookies = await page.context.cookies()

        print("Got cookies")
        with open(f'cookies{email}.json', 'w') as f:
            json.dump(cookies, f)
        print("Logged in and saved cookies.")
        return

    # We ran into an gmail code request
    # await page.wait_for_load_state('networkidle')
    if not page.url.startswith('https://www.linkedin.com/feed'):
        try:
            line = await aioconsole.ainput('Enter the code that arrived in the email')
            elem = page.locator(
                "xpath=//input[@placeholder = '6 digit code' or @placeholder = 'Enter code']")
            await elem.fill(line)
            await page.keyboard.press('Enter')
            await asyncio.sleep(3)
        except Exception as e:
            print(e)
            print(await page.content())

    # Check if we failed
    if page.url.startswith('https://www.linkedin.com/feed'):
        print("Logged in")
    else:
        print("Error on loggin")
        print(await page.content())
        return
    cookies = await page.context.cookies()
    print("Got cookies")
    with open(f'cookies{email}.json', 'w') as f:
        json.dump(cookies, f)
    print("Logged in and saved cookies.")


async def load_cookies(context, username):
    try:
        with open(f'cookies{username}.json', 'r') as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        print("Loaded cookies.")
        return True
    except FileNotFoundError:
        print("No saved cookies found.")
        return False


async def load_new_account(browser, loading_next=False):
    file_name = "acc_usage_tracking.json"
    if os.path.exists(file_name):
        with open(file_name, "r") as file:
            profiles = json.load(file)
    else:
        return -1, None

    if(not "profile_id" in os.environ):
        os.environ["profile_id"] = "0"
    profile_index = int(os.environ["profile_id"])

    if loading_next:
        profiles[profile_index]['remaining_uses'] = 0
        profile_index = (profile_index+1) % len(profiles)
        os.environ["profile_id"] = str(profile_index)

    if profiles[profile_index]['remaining_uses'] == 0:
        if int((datetime.datetime.strptime(profiles[profile_index]['last_used_date'], '%Y-%m-%d %H:%M:%S') - datetime.datetime.now()).total_seconds()//(3600)) >= 25:
            profiles[profile_index]['last_used_date'] = datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S")
            profiles[profile_index]['remaining_uses'] = 147
        else:
            return -1, None

    with open(file_name, "w") as file:
        json.dump(profiles, file, indent=4)
    username = profiles[profile_index]['name']
    if(config['credentials'].get(username.split('@')[0]) is None):
        raise Exception("Error non existing username called")

    password = config['credentials'].get(username.split('@')[0])

    context = await browser.new_context()
    page = await context.new_page()

    await stealth_async(page)
    await login_and_get_cookies(page, username, password, context)
    await context.close()

    return profiles[profile_index]['remaining_uses'], username


async def save_profile_counts(count):
    if("profile_id" not in os.environ):
        return
    profile_index = int(os.environ['profile_id'])

    file_name = "acc_usage_tracking.json"
    if os.path.exists(file_name):
        with open(file_name, "r") as file:
            profiles = json.load(file)
    profiles[profile_index]['remaining_uses'] = count
    with open(file_name, "w") as file:
        json.dump(profiles, file, indent=4)


# SAVING AND LOADING POSTS

def save_to_json(posts, person):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    file_name = f"JSON_DATA/{person}_posts_{today}.json"
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
    existing_keys = []
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
        new_keys.append({'key': key})

    with open(file_name, 'w') as file:
        json.dump(new_keys, file, indent=4)

    return new_keys


def get_visited_profiles():
    file_name = "visited_profiles.json"
    if os.path.exists(file_name):
        with open(file_name, 'r') as file:
            scraped_people = json.load(file)
            return scraped_people
    else:
        return dict()


def save_visited_profiles(people):
    file_name = "visited_profiles.json"
    with open(file_name, "w") as file:
        json.dump(people, file, indent=4)

# GPT PROCESSING


def call_chatgpt_api(post_text):
    """response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"Determine if the following post is on an approved topic: {post_text}",
        max_tokens=10
    )
    return "approved" in response.choices[0].text.lower()"""
    return Gpt_check_topic.check_topic(post_text)


async def process_posts(posts, topics):
    approved_posts = []

    tasks = [Gpt_check_topic.check_topic(posts[i], i, topics) for i in range(
        len(posts)) if 'post_text' in posts[i]]
    responses = await asyncio.gather(*tasks)
    approved_posts = [
        response for response in responses if 'post_text' in response]
    return approved_posts

# SERVER START


def start_flask_server():
    print("Starting Flask server...")
    subprocess.Popen(['python', 'flask_server.py'])
    print("Flask server started.")

# SCRAPING


rate_limiter = Limiter(1/5)


async def scrape_feed(browser, username, saved_keys, blacklist):
    context = await browser.new_context()
    page = await context.new_page()
    await stealth_async(page)
    await page.goto('https://www.linkedin.com/feed/', timeout=60000)

    await load_cookies(context, username)
    if not page.url.startswith('https://www.linkedin.com/feed'):
        print("Cookies invalid, logging in...")
        # Replace securely
        await login_and_get_cookies(page, username, config['credentials'][username.split('@')[0]])
        await page.goto('https://www.linkedin.com/feed/', timeout=60000)

    posts, saved_keys = await fetch_posts(page, saved_keys, blacklist)
    # links = await scrape_link_only(page, posts, "//*[@data-finite-scroll-hotkey-item]")
    await context.close()
    return posts, saved_keys


async def scrape_person(browser, person, extension, saved_keys, blacklist, sem, username):
    async with sem:
        await rate_limiter.wait()
        context = await browser.new_context()
        try:
            await load_cookies(context, username)

            page = await context.new_page()
            # await stealth_async(page)
            url = f'https://www.linkedin.com/in/{person}/recent-activity/{extension}'
            await page.goto(url, timeout=90000)
            posts, saved_keys = await fetch_posts_person(page, person, extension, saved_keys, blacklist)
        # links = await scrape_link_only(page, posts, "./ul[1]/li")
            await context.close()
            return {'posts': posts, 'ext': extension}
        except Exception as e:
            print(e)
            print(page.url)
            await context.close()
            return {'posts': [], 'ext': extension}


async def main(taskQueue: Queue):
    # saved_keys = load_visited_posts()
    saved_keys = set()

    blacklist = config['blacklist']
    extensions = config['extensions']

    visited_profiles = get_visited_profiles()

    sem = asyncio.Semaphore(2)
    async with async_playwright() as p:
        print(datetime.datetime.now())
        browser = await p.chromium.launch(headless=True)
        # posts, saved_keys = await scrape_feed(browser, saved_keys, blacklist)

        remaining_calls, curr_username = await load_new_account(browser)
        if remaining_calls == -1:
            await browser.close()
            return

        tasks = []
        visited = set()
        while not taskQueue.empty():
            new_block = taskQueue.get()
            for person in new_block['stalklist']:
                if visited_profiles.get(person) and (datetime.datetime.now() - datetime.datetime.strptime(visited_profiles[person], '%Y-%m-%d %H:%M:%S')).total_seconds()//(3600) < 12:
                    print((datetime.datetime.now() - datetime.datetime.strptime(
                        visited_profiles[person], '%Y-%m-%d %H:%M:%S')).total_seconds()//(3600))
                    continue
                if remaining_calls == -1:
                    break

                visited_profiles[person] = datetime.datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S")
                for extension in extensions:
                    tasks += [asyncio.create_task(scrape_person(
                        browser, person, extension, saved_keys, blacklist, sem, curr_username))]
                    remaining_calls -= 1
                    if remaining_calls <= 0:
                        remaining_calls, curr_username = await load_new_account(browser)

                # for extension in extensions:
                # tasks += await scrape_person(browser, person, extension, saved_keys, blacklist)

                results = await asyncio.gather(*tasks)
                out = []

                for result in results:
                    for post in result['posts']:

                        if (post['data_id']) and (not post['data_id'] in visited):
                            out.append(post)
                            visited.add(post['data_id'])

            # out = posts + out
            # out = await process_posts(out)
                save_to_json(out, person)
        save_visited_profiles(visited_profiles)
        await save_profile_counts(remaining_calls)
        await browser.close()
    print(datetime.datetime.now())
    # start_flask_server()


if __name__ == "__main__":
    q = Queue()
    q.put({"stalklist": ["kevinolearytv", "williamhgates", "mattgray1"]})
    asyncio.run(main(q))
