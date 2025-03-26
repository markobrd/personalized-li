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

def fetch_posts(driver):
    """
    Fetch posts from a LinkedIn feed URL.
    
    Parameters:
    - url (str): URL of the LinkedIn feed page.
    - headers (dict): HTTP headers to include in the request.
    
    Returns:
    - List of dictionaries containing post data.
    """
    #response = requests.get(url, headers=headers)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, 0);")

    response = driver.find_elements(By.CLASS_NAME,'scaffold-finite-scroll__content')
    # Check if the response is successful
    """if response.status_code != 200:
        print(f"Failed to fetch posts: {response.status_code}")
        return []
    """

    # Wait for 30 seconds after fetching the page
    time.sleep(5)
    
    # Parse the HTML content
    soup = BeautifulSoup(response[0].get_attribute('innerHTML'), 'html.parser')
    
    posts = []
    
    # Find the container holding the posts
    feed_content = soup
    if not feed_content:
        print("Feed content not found.")
        return posts
    
    # Loop through each post element
    for post_div in feed_content.select("[data-finite-scroll-hotkey-item]"):
        post_data = {}
        
        # Extract actor's information
        actor = post_div.find('div', class_='update-components-actor')
        if actor:
            meta = actor.find('div', class_='update-components-actor__meta')
            if meta:
                title_link = meta.find('a', class_='app-aware-link')
                if title_link:
                    post_data['actor_name'] = title_link.get_text(strip=True)
                    post_data['actor_profile'] = title_link['href']
                    
                description = meta.find('span', class_='update-components-actor__description')
                if description:
                    post_data['actor_description'] = description.get_text(strip=True)
                    
                time_info = meta.find('a', class_='app-aware-link')
                if time_info:
                    post_data['post_time'] = time_info.get_text(strip=True)
        
        # Extract the post content
        post_content = post_div.find('div', class_='feed-shared-inline-show-more-text')
        if post_content:
            post_data['post_text'] = post_content.get_text(strip=True)
        
        # Extract any event information
        event = post_div.find('section', class_='update-components-event')
        if event:
            event_info = event.find('a', class_='app-aware-link')
            if event_info:
                post_data['event_title'] = event_info.get_text(strip=True)
                post_data['event_link'] = event_info['href']
        
        posts.append(post_data)
    
    return posts

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

def generate_html_alternative(approved_posts, driver):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    html_content = f"<html><head><title>Approved Posts - {today}</title></head><body>"
    elements = driver.find_elements(By.CLASS_NAME,'scaffold-finite-scroll__content')
    elements = elements[0].find_elements(By.XPATH, "//*[@data-finite-scroll-hotkey-item]")
    for index in approved_posts:
        response = elements[index]
        response1 = response.find_elements(By.CLASS_NAME, 'feed-shared-control-menu')
        response1 = response1[0].find_elements(By.XPATH, './div[1]/button[1]')
        driver.execute_script("arguments[0].click();", response1[0])
        time.sleep(1)
        response2 = response.find_elements(By.CLASS_NAME, 'feed-shared-control-menu')
        response2 = response2[0].find_elements(By.XPATH, './div[1]/div[1]/div[1]/ul[1]/li[3]/div[1]')
        driver.execute_script("arguments[0].click();", response2[0])
        time.sleep(1)
        response3 = driver.find_elements(By.ID,'feed-components-shared-embed-modal__snippet')
        if(len(response3) > 0):
            link = response3[0].get_attribute("value")
            html_content+=link
            print(link)
        time.sleep(1)
        esc = driver.find_element(By.XPATH, "//*[@aria-label='Dismiss']")
        if esc:
            esc.click()
        time.sleep(1)
    html_content+= "</body></html>"
    with open(f"approved_posts_{today}.html", 'w') as file:
        file.write(html_content)
    print(html_content)
    return True

if __name__ == "__main__":
    driver = setup_driver()
    
    try:
        if not check_login_status(driver):
            login(driver)
        
        time.sleep(2)
        posts = fetch_posts(driver)
        #print(posts)
        approved_posts = process_posts(posts[:10])
        print(approved_posts)
        new_posts = save_to_json(posts)

        generate_html_alternative(approved_posts, driver)
        
    finally:
        driver.quit()




