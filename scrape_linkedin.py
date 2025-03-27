import requests
from bs4 import BeautifulSoup
import json
import time
import datetime
import os
import pickle
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
import yaml
import Ollama_check_topic
from scrape_functions import *

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
# CHROMEDRIVER_PATH = '/path/to/chromedriver'  # Ensure this path is correct

def setup_driver():
    chrome_options = Options()
    user_profile_path = 'C:/Users/Uros/AppData/Local/Google/Chrome/User Data/Default'
    #chrome_options.add_argument("--headless")  # Run in headless mode if you don't need the UI
    chrome_options.add_argument(f'user-data-dir={user_profile_path}')
    # service = Service(CHROMEDRIVER_PATH)
    # driver = webdriver.Chrome(service=service, options=chrome_options)
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
    return post_text

def call_ollama_api(post_text):
    res = Ollama_check_topic.check_topic(post  =post_text, topics=APPROVED_TOPICS)
    print(res)
    return "True" in res


def process_posts(posts):
    approved_posts = []
    for i in range(len(posts)):
        try:
            #If the model is about given topics we save its post index so we can copy the embeding link later
            print(posts[i]['post_text'])
            if True or call_ollama_api(posts[i]['post_text']):
                approved_posts.append(i)
        except:
            continue
    return approved_posts

def save_to_json(posts):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    file_name = f"posts_{today}.json"
    
    if os.path.exists(file_name):
        with open(file_name, 'r') as file:
            existing_posts = json.load(file)
    else:
        existing_posts = []
    
    new_posts = [post for post in posts if post not in existing_posts]
    
    with open(file_name, 'w') as file:
        json.dump(existing_posts + new_posts, file, indent=4)
    
    return new_posts

def generate_html(approved_posts):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    html_content = f"<html><head><title>Approved Posts - {today}</title></head><body>"
    
    for post in approved_posts:
        html_content += f"<h2><a href='{post['url']}'>{post['name']}</a></h2>"
        html_content += f"<p>{post['text']}</p>"
        html_content += "<h3>Comments:</h3>"
        for comment in post['comments']:
            html_content += f"<p><a href='{comment['profile_url']}'>{comment['name']}</a>: {comment['text']}</p>"
    
    html_content += "</body></html>"
    
    with open(f"approved_posts_{today}.html", 'w') as file:
        file.write(html_content)

def save_html(html_content):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    with open(f"approved_posts_{today}.html", 'w') as file:
        file.write(html_content)

if __name__ == "__main__":
    driver = setup_driver()
    
    try:
        if not check_login_status(driver):
            login(driver)
        

        time.sleep(2)
        """
        posts1 = fetch_posts_person(driver, "nishkambatta")
        approved_posts = process_posts(posts1)
        print(approved_posts)
        print("\n\n\n")
        print(generate_html_alt(approved_posts, driver, "./ul[1]/li"))
        """
        #posts = fetch_posts_person(driver, "nishkambatta", "all")
        #posts = fetch_posts_person(driver, "nishkambatta", "comments")
        posts = fetch_posts_person(driver, "nishkambatta", "reactions")
        print(posts)
        approved_posts = process_posts(posts)
        print(approved_posts)
        new_posts = save_to_json(posts)

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        html = f"<html><head><title>Approved Posts - {today}</title></head><body>"

        #html += generate_html_alt(approved_posts, driver, "//*[@data-finite-scroll-hotkey-item]")
        html += generate_html_alt(approved_posts, driver, "./ul[1]/li")
        html += "</body></html>"

        save_html(html)
        
    finally:
        driver.quit()




