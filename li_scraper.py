# scrape_linkedin.py

import requests
from bs4 import BeautifulSoup
import json
import datetime
import os

# Configuration
LINKEDIN_URL = "https://www.linkedin.com"
APPROVED_TOPICS = ["Artificial Intelligence", "Business Intelligence"]  # Replace with your approved topics

def fetch_posts():
    response = requests.get(LINKEDIN_URL)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    posts = []
    for post in soup.find_all('div', class_='post-class'):  # Adjust the class selector as needed
        post_data = {
            'url': post.find('a', class_='post-url-class')['href'],
            'name': post.find('a', class_='profile-url-class').text.strip(),
            'profile_url': post.find('a', class_='profile-url-class')['href'],
            'text': post.find('div', class_='post-text-class').text.strip(),
            'comments': []
        }
        
        for comment in post.find_all('div', class_='comment-class'):  # Adjust the class selector as needed
            comment_data = {
                'name': comment.find('a', class_='commenter-url-class').text.strip(),
                'profile_url': comment.find('a', class_='commenter-url-class')['href'],
                'text': comment.find('div', class_='comment-text-class').text.strip()
            }
            post_data['comments'].append(comment_data)
        
        posts.append(post_data)
    
    return posts

def call_chatgpt_api(post_text):
    # Call OpenAI API to check if the topic is approved
    # Replace with actual API call and response handling
    return post_text

def process_posts(posts):
    approved_posts = []
    for post in posts:
        if call_chatgpt_api(post['text']):
            post['approved'] = True
            approved_posts.append(post)
        else:
            post['approved'] = False
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

def main():
    posts = fetch_posts()
    approved_posts = process_posts(posts)
    new_posts = save_to_json(posts)
    print(generate_html(approved_posts))

if __name__ == "__main__":
    main()
