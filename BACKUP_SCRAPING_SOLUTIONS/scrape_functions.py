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



def fetch_posts(driver, saved_keys, blacklist = []):

    url = 'https://www.linkedin.com/feed/'
    driver.get(url)
    #response = requests.get(url, headers=headers)
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    driver.execute_script("window.scrollTo(0, 0);")


    response = WebDriverWait(driver, 10).until(
        lambda d: driver.find_elements(By.CLASS_NAME,'scaffold-finite-scroll__content')
    )

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
    
    iter = 0
    # Loop through each post element
    for post_div in feed_content.select("[data-finite-scroll-hotkey-item]"):
        post_data = {}

        #data_id = post_div.get('data-id', "")
        post_content = post_div.find('div', class_='feed-shared-inline-show-more-text')
        if not post_content:
            iter+=1
            print("skipped no_content "+str(iter)+"\n")
            continue
        data_id = post_content.get_text(strip=True)[:35]
        if data_id == "" or len(post_div.get('data-id', "")) > 35 or (data_id in saved_keys):
            iter+=1
            print("skipped not_a_post"+str(iter)+"\n")
            continue

        profile_link = post_div.find('div', class_ = 'update-components-actor__container')
        if not profile_link:
            iter+=1
            continue

        profile_link = profile_link.find('a')
        if not profile_link or (profile_link.get('href').split("/")[3] in blacklist) or (profile_link.get('href').split("/")[4].split("?")[0] in blacklist):
            iter+=1
            continue

        saved_keys.add(data_id)
        profile_link = profile_link.get('href')
        post_data['profile_link'] = profile_link
        post_data['data_id'] = data_id

        post_data['id'] = iter
        
        #Get link to the profile img of the user 
        #TO DO FIX: The issue is when the post is reposted, the person commented on a post or reacted. Find a way around this
        img_link = post_div.find('div', class_= "ivm-view-attr__img-wrapper")
        img_link = img_link.find('img')
        if img_link:
            post_data['img_link'] = img_link.get('src')

        #Get name of the poster
        #post_div.find('span', {'aria-hidden': 'true'}).get_text(strip=True)
        name = post_div.find('span', class_='update-components-actor__title')
        if name:
            name = name.find('span').get_text(strip=True)
            name = name[:len(name)//2]
            post_data['name'] = name
        else:
            post_data['name'] = ""


        # Extract the rank        
        rank = post_div.find('span', class_='update-components-actor__supplementary-actor-info')
        if rank:
            rank = rank.get_text(strip=True)
            rank = rank[:len(rank)//2]
            post_data['rank'] = rank
        else:
            post_data['rank'] = ""

        # Extract the description
        description = post_div.find('span', class_='update-components-actor__description')
        if description:
            description = description.get_text(strip=True)
            description = description[:len(description)//2]
            post_data['description'] = description
        else:
            post_data['description'] = ""

        #Extract the time posted
        time_posted = post_div.find('span', class_='update-components-actor__sub-description')
        if time_posted:
            time_posted = time_posted.get_text(strip=True)
            post_data['time_posted'] = time_posted
        else:
            post_data['time_posted'] = ""

        
        print("name: " + post_data['name']+"\n")
        print("profile_link: " +post_data['profile_link'] +"\n")
        print("rank: "+post_data['rank'] +"\n")
        print("description: "+post_data['description']+"\n")
        print("time_posted: "+post_data['time_posted']+"\n")

        # Extract the post content
        post_content = post_div.find('div', class_='feed-shared-inline-show-more-text')
        if post_content:
            for br in post_content.find_all('br'):
                br.replace_with('\n')
            post_data['post_text'] = post_content.text[:-9]
        
        posts.append(post_data)
        iter+=1
    
    return posts, saved_keys


#Scraping posts from a given person
def fetch_posts_person(driver, person, extension, saved_keys, blacklist = []):

    url = 'https://www.linkedin.com/in/'+ person + '/recent-activity/' + extension
    driver.get(url)


    response = WebDriverWait(driver, 10).until(
        lambda d: driver.find_elements(By.CLASS_NAME, 'scaffold-finite-scroll__content')
    )
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    #response = driver.find_elements(By.CLASS_NAME,'scaffold-finite-scroll__content')
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
    iter = 0
    for post_div in feed_content.find_all("li", recursive=False):
        post_data = {}

        content = post_div.find("span", class_="break-words tvm-parent-container")
        if not content:
           iter+=1
           print("skip content")
           continue

        post_id_elem = post_div.find_all('div', class_ ="feed-shared-update-v2")[0]
        #data_id = post_id_elem.get('data-urn', "")
        data_id = content.text.strip()[:35]
        if((data_id in saved_keys) or len(post_id_elem.get('data-id', "")) > 35):
            iter+=1
            print("skip data_id")
            continue

        profile_link = post_div.find('div', class_ = 'update-components-actor__container')
        if not profile_link:
            iter+=1
            print("skip link 1")
            continue

        profile_link = profile_link.find('a')
        if not profile_link or (profile_link.get('href').split("/")[3] in blacklist) or (profile_link.get('href').split("/")[4].split("?")[0] in blacklist):
            iter+=1
            print("skip link 2")
            continue
        

        saved_keys.add(data_id)
        profile_link = profile_link.get('href')
        post_data['profile_link'] = profile_link

        for br in content.find_all('br'):
            br.replace_with('\n')

        post_data['post_text'] = content.text[:-9]
        post_data['data_id'] = data_id
        post_data['id'] = iter

        #Get link to the profile img of the user 
        img_link = post_div.find('div', class_= "ivm-view-attr__img-wrapper")
        img_link = img_link.find('img')
        if img_link:
            post_data['img_link'] = img_link.get('src')

        #Get name of the poster
        #post_div.find('span', {'aria-hidden': 'true'}).get_text(strip=True)
        name = post_div.find('span', class_='update-components-actor__title')
        if name:
            name = name.find('span').get_text(strip=True)
            name = name[:len(name)//2]
            post_data['name'] = name
        else:
            post_data['name'] = ""


        # Extract the rank        
        rank = post_div.find('span', class_='update-components-actor__supplementary-actor-info')
        if rank:
            rank = rank.get_text(strip=True)
            rank = rank[:len(rank)//2]
            post_data['rank'] = rank
        else:
            post_data['rank'] = ""

        # Extract the description
        description = post_div.find('span', class_='update-components-actor__description')
        if description:
            description = description.get_text(strip=True)
            description = description[:len(description)//2]
            post_data['description'] = description
        else:
            post_data['description'] = ""

        #Extract the time posted
        time_posted = post_div.find('span', class_='update-components-actor__sub-description')
        if time_posted:
            time_posted = time_posted.get_text(strip=True)
            post_data['time_posted'] = time_posted
        else:
            post_data['time_posted'] = ""

        print("name: " + post_data['name']+"\n")
        print("profile_link: " +post_data['profile_link'] +"\n")
        print("rank: "+post_data['rank'] +"\n")
        print("description: "+post_data['description']+"\n")
        print("time_posted: "+post_data['time_posted']+"\n")

        posts.append(post_data)
        iter+=1
    return posts, saved_keys


def scrape_link_only(driver, aproved_posts, xpath):
    links = []
    #driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    #time.sleep(1)
    elems = driver.find_elements(By.CLASS_NAME, "scaffold-finite-scroll__content")[0]
    elems = elems.find_elements(By.XPATH, xpath)
    print(len(elems))
    for post in aproved_posts:
        index = post['id']
        elem3 = elems[index].find_elements(By.CLASS_NAME, 'artdeco-dropdown')
        if len(elem3) == 0:
            continue
        else:
            elem3 = elem3[0]
        elem3 = elem3.find_elements(By.XPATH, './button[1]')
        if(len(elem3) > 0):
            driver.execute_script("arguments[0].click();", elem3[0])
    
    time.sleep(1)
    driver.execute_script("window.focus();")
    for post in aproved_posts:
        index = post['id']
        elem3 = elems[index].find_elements(By.CLASS_NAME, 'artdeco-dropdown')
        if len(elem3) == 0:
            continue
        else:
            elem3 = elem3[0]
        elem3 = elem3.find_elements(By.XPATH, './div[1]/div[1]/ul[1]/li[2]/div[1]')
        print(len(elem3))
        if len(elem3) > 0:
            driver.execute_script("arguments[0].click();", elem3[0])
            link = driver.find_element(By.CLASS_NAME, 'artdeco-toast-item__cta')
            p = link.get_attribute("href")
            post['post_link'] = p
            links.append(p)

    print(links)
    return links



def generate_html_alt(approved_posts, driver, xpath):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    html_content = "<br><br>"
    elements = driver.find_elements(By.CLASS_NAME,'scaffold-finite-scroll__content')

    elements = elements[0].find_elements(By.XPATH, xpath)

    for post in approved_posts:
        index = post['id']
        response = elements[index]
        #clicks 3 dots button
        try:
            response1 = response.find_elements(By.CLASS_NAME, 'feed-shared-control-menu')
            response1 = response1[0].find_elements(By.XPATH, './div[1]/button[1]')
            driver.execute_script("arguments[0].click();", response1[0])

            #clicks embed code button 

            response2 = response.find_elements(By.CLASS_NAME, 'feed-shared-control-menu')
            #wait until the dropdown menu shows
            response2 = WebDriverWait(response2[0], 3).until(
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
            WebDriverWait(driver, 3).until(
            lambda d: response3.get_attribute("value").strip() != ""
            )
        except:
            continue
        #if we can, copy the embedding code
        if response3:
            iframe = response3.get_attribute("value")
            link = BeautifulSoup(iframe).find("iframe").get('src')
            html_content+="""<div class="card">"""
            #html_content+=link
            html_content+=f"""<iframe src = {link} height = 900 width ="504" frameborder="0"></iframe></div>"""

            #html_content+="\n</div>"
        #close poppup
        if esc:
            esc.click()
    return html_content


