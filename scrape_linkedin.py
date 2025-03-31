import yaml
import Ollama_check_topic
import Gpt_check_topic
from scrape_functions import *
import http.server
import socketserver
import webbrowser
import asyncio
import threading
from flask import Flask, send_from_directory
from html_components import *

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
    return Gpt_check_topic.check_topic(post_text)

def call_ollama_api(post_text):
    res = Ollama_check_topic.check_topic(post  =post_text, topics=APPROVED_TOPICS)
    print(res)
    return "True" in res


async def process_posts(posts):
    approved_posts = []

    tasks = [Gpt_check_topic.check_topic(posts[i]['post_text'], i) for i in range(len(posts)) if 'post_text' in posts[i]]
    responses = await asyncio.gather(*tasks)
    """for i in range(len(responses)):
        try:
            #If the model is about given topics we save its post index so we can copy the embeding link later
            print(posts[i]['post_text'])
            if posts[i]['post_text'] and Gpt_check_topic.check_topic(posts[i]['post_text']):
                approved_posts.append(i)
        except:
            continue"""
    approved_posts = [index for index in responses if index>=0]
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

class MyHttpServer(socketserver.TCPServer):
    allow_reuse_address = True  # Allows quick restart after shutdown

# Function to start the server
def start_server():
    with MyHttpServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        httpd.serve_forever()
    
app = Flask(__name__)

@app.route('/')
def serve_file():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return send_from_directory('.', f'approved_posts_{today}.html')

def run_flask():
    app.run(port=PORT)

async def main():
    driver = setup_driver()
    
    try:
        if not check_login_status(driver):
            login(driver)
        

        time.sleep(1)

        """posts1 = fetch_posts_person(driver, "nishkambatta")
        approved_posts = process_posts(posts1)
        print(approved_posts)
        print("\n\n\n")
        print(generate_html_alt(approved_posts, driver, "./ul[1]/li"))"""
        

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        html = html_top

        """posts_all = fetch_posts_person(driver, "nishkambatta", "all")
        approved_posts_all = await process_posts(posts_all[:5])
        html += generate_html_alt(approved_posts_all, driver, "./ul[1]/li")

        posts_comments = fetch_posts_person(driver, "nishkambatta", "comments")
        approved_posts_comments = await process_posts(posts_comments[:10])
        html += generate_html_alt(approved_posts_comments, driver, "./ul[1]/li")

        posts_reactions = fetch_posts_person(driver, "nishkambatta", "reactions")
        approved_posts_reactions = await process_posts(posts_reactions[:10])
        html += generate_html_alt(approved_posts_reactions, driver, "./ul[1]/li")"""

        posts_feed = fetch_posts(driver)
        approved_posts_feed = await process_posts(posts_feed[:10])
        html += generate_html_alt(approved_posts_feed, driver, "//*[@data-finite-scroll-hotkey-item]")

        #new_posts = save_to_json(posts)




        html += html_bottom

        save_html(html)


        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()

        # Open the HTML file in the default browser
        webbrowser.open(f"http://localhost:{PORT}")

        # Check if the tab is closed
    finally:
        driver.quit()
        print("finished...")

if __name__ == "__main__":
    asyncio.run(main())




