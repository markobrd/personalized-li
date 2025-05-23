import yaml
#import Ollama_check_topic
import Gpt_check_topic
from scrape_functions import *
import http.server
import socketserver
import webbrowser
import asyncio
import threading
from html_components import *
import subprocess
from concurrent.futures import ThreadPoolExecutor
from selenium_driverless import webdriver
from selenium_driverless.types.by import By
from asynciolimiter import Limiter
import datetime

# Load the config
with open('config.yaml') as config_file:
    config = yaml.safe_load(config_file)

# Configuration
USERNAME = config['credentials']['username']
PASSWORD = config['credentials']['password']
LOGIN_URL = config['urls']['login_url']
FETCH_URL = config['urls']['fetch_url']
TIMEOUT = config['settings']['timeout']
APPROVED_TOPICS = config['topics']  # Replace with your approved topics
PORT = 5000

# CHROMEDRIVER_PATH = '/path/to/chromedriver'  # Ensure this path is correct

def setup_driver(incognito = False):
    chrome_options = Options()
    user_profile_path = 'C:/Users/Uros/AppData/Local/Google/Chrome/User Data/Default'
    #chrome_options.add_argument("--headless")  # Run in headless mode if you don't need the UI
    chrome_options.add_argument(f'user-data-dir={user_profile_path}')
    # service = Service(CHROMEDRIVER_PATH)
    if incognito:
        chrome_options.add_argument("--incognito")

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def save_cookies(driver):
    pickle.dump(driver.get_cookies(), open("cookies.pkl", "wb"))

def load_cookies(driver):
    if Path("cookies.pkl").exists():
        cookies = pickle.load(open("cookies.pkl", "rb"))
        if cookies:
            # print("cookie domain")
            for cookie in cookies:
                # print(cookie['domain'])
                driver.add_cookie(cookie)
            driver.refresh()
            return True
    return False

def login(driver):
    # Go to login page
    driver.get(LOGIN_URL)
    # Try to load cookies
    if load_cookies(driver) : return
    # Login if needed (don't forget two step verification, if it's set up)
    if check_login_status(driver):
        username_field = driver.find_element(By.ID, "username")
        password_field = driver.find_element(By.ID, "password")
        username_field.send_keys(USERNAME)
        password_field.send_keys(PASSWORD)
        password_field.send_keys(Keys.RETURN)
    
    try:
        WebDriverWait(driver, TIMEOUT).until(
            EC.url_contains("feed")  # Check if the URL contains 'feed' indicating a successful login
        )
        save_cookies(driver=driver)
        print("Login successful.")
    except TimeoutException:
        print("Login failed or still logging in.")

def check_login_status(driver):
    return 'login' in driver.current_url


def call_chatgpt_api(post_text):
    """response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"Determine if the following post is on an approved topic: {post_text}",
        max_tokens=10
    )
    return "approved" in response.choices[0].text.lower()"""
    return Gpt_check_topic.check_topic(post_text)

"""def call_ollama_api(post_text):
    res = Ollama_check_topic.check_topic(post  =post_text, topics=APPROVED_TOPICS)
    print(res)
    return "True" in res"""


async def process_posts(posts):
    approved_posts = []

    tasks = [Gpt_check_topic.check_topic(posts[i], i) for i in range(len(posts)) if 'post_text' in posts[i]]
    responses = await asyncio.gather(*tasks)
    """for i in range(len(responses)):
        try:
            #If the model is about given topics we save its post index so we can copy the embeding link later
            print(posts[i]['post_text'])
            if posts[i]['post_text'] and Gpt_check_topic.check_topic(posts[i]['post_text']):
                approved_posts.append(i)
        except:
            continue"""
    approved_posts = [response for response in responses if 'post_text' in response]
    return approved_posts

def save_to_json(posts):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    file_name = f"JSON_DATA/posts_{today}.json"
    old_posts = []
    if os.path.exists(file_name):
        with open(file_name, 'r') as file:
            old_posts = json.load(file)
    with open(file_name, 'w') as file:
        json.dump(old_posts+posts, file, indent=4)
    
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

def save_html(html_content):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    with open(f"saved_feeds/approved_posts_{today}.html", 'w') as file:
        file.write(html_content)


# Function to start the server
def start_flask_server():
    print("Starting Flask server...")
    subprocess.Popen(['python', 'flask_server.py'])
    print("Flask server started.")    
    
async def run_for_account(url):
    
    options = webdriver.ChromeOptions()
    #options.add_argument("--headless=new")
    async with webdriver.Chrome(options=options) as driver:
        await driver.get(url)
        await asyncio.sleep(10.0)
        # Perform your scraping tasks here
        print(f"Opened: {url}")

async def main():
    print(datetime.datetime.now())
    driver = setup_driver(False)
    try:


        if not check_login_status(driver):
            login(driver)

        saved_keys = load_visited_posts()

        blacklist = config["blacklist"]
        posts_all, saved_keys = fetch_posts_person(driver, "nishkambatta", "all", saved_keys, blacklist)
        approved_posts_all = await process_posts(posts_all[:5])
        link = scrape_link_only(driver, approved_posts_all, "./ul[1]/li")

        posts_comments, saved_keys = fetch_posts_person(driver, "nishkambatta", "comments", saved_keys, blacklist)
        approved_posts_comments = await process_posts(posts_comments[:10])
        links = scrape_link_only(driver, approved_posts_comments, "./ul[1]/li")

        posts_reactions, saved_keys = fetch_posts_person(driver, "nishkambatta", "reactions", saved_keys, blacklist)
        approved_posts_reactions = await process_posts(posts_reactions[:10])
        links = scrape_link_only(driver, approved_posts_reactions, "./ul[1]/li")

        posts_feed, saved_keys = fetch_posts(driver, saved_keys, blacklist)
        approved_posts_feed = await process_posts(posts_feed)
        links = scrape_link_only(driver, approved_posts_feed, "//*[@data-finite-scroll-hotkey-item]")

        new_posts = save_to_json(approved_posts_feed+approved_posts_all+approved_posts_comments+approved_posts_reactions)

        save_visited_posts(saved_keys)

        # Check if the tab is closed
    finally:
        #start_flask_server()
        #await driver.close()
        print(datetime.datetime.now())
        print("finished...")

if __name__ == "__main__":
    asyncio.run(main())




