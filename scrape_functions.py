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
    time.sleep(0.5)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(0.5)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)

    response = driver.find_elements(By.CLASS_NAME,'scaffold-finite-scroll__content')
    # Check if the response is successful
    """if response.status_code != 200:
        print(f"Failed to fetch posts: {response.status_code}")
        return []
    """

    # Wait for 30 seconds after fetching the page
    time.sleep(1)
    
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


#Scraping posts from a given person
def fetch_posts_person(driver, person, extension):

    url = 'https://www.linkedin.com/in/'+ person + '/recent-activity/' + extension
    driver.get(url)


    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    
    response = driver.find_elements(By.CLASS_NAME,'scaffold-finite-scroll__content')
    response = response[0].find_element(By.XPATH, './ul[1]')
    # Parse the HTML content
    soup = BeautifulSoup(response.get_attribute('innerHTML'), 'html.parser')
    
    posts = []
    
    # Find the container holding the posts
    feed_content = soup
    if not feed_content:
        print("Feed content not found.")
        return posts
    
    # Loop through each post element
    for post_div in feed_content.find_all("li", recursive=False):
        post_data = {}

        content = post_div.find("span", class_="break-words tvm-parent-container")
        if content:
           post_data['post_text'] = content.text.strip()
        posts.append(post_data)
    return posts


def generate_html_alt(approved_posts, driver, xpath):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    html_content = "<br><br>"
    elements = driver.find_elements(By.CLASS_NAME,'scaffold-finite-scroll__content')

    elements = elements[0].find_elements(By.XPATH, xpath)

    for index in approved_posts:
        response = elements[index]
        #clicks 3 dots button
        response1 = response.find_elements(By.CLASS_NAME, 'feed-shared-control-menu')
        response1 = response1[0].find_elements(By.XPATH, './div[1]/button[1]')
        driver.execute_script("arguments[0].click();", response1[0])
        #time.sleep(1)

        #clicks embed code button 

        response2 = response.find_elements(By.CLASS_NAME, 'feed-shared-control-menu')
        #wait until the dropdown menu shows
        response2 = WebDriverWait(response2[0], 10).until(
        lambda d: response2[0].find_element(By.XPATH, './div[1]/div[1]/div[1]/ul[1]/li[3]/div[1]')
        )
        driver.execute_script("arguments[0].click();", response2)

        #copies link of the embeding then closes the poppup
        esc = WebDriverWait(driver, 3).until(
        EC.presence_of_element_located((By.XPATH, "//*[@aria-label='Dismiss']"))
        )
        check = driver.find_elements(By.ID, 'embed-modal-label')
        if not check:
            esc.click()
            continue
        response3 = driver.find_element(By.ID,'feed-components-shared-embed-modal__snippet')
        WebDriverWait(driver, 10).until(
        lambda d: response3.get_attribute("value").strip() != ""
        )

        #if we can, copy the embedding code
        if response3:
            link = response3.get_attribute("value")
            html_content+="""<div class="card">"""
            html_content+=link
            print(link)
            html_content+="\n</div>"
        #close poppup
        if esc:
            esc.click()
    return html_content