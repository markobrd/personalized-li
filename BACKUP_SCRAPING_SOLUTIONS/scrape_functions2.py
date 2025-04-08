import asyncio
from bs4 import BeautifulSoup
from selenium_driverless.sync.webdriver import Chrome
from selenium_driverless.types.by import By
import time

async def fetch_posts(driver, saved_keys, blacklist=[]):
    url = 'https://www.linkedin.com/feed/'
    await driver.get(url)
    await asyncio.sleep(1)

    await driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
    await asyncio.sleep(1)
    await driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    await asyncio.sleep(1)
    await driver.execute_script("window.scrollTo(0, 0);")

    elements = await driver.find_elements(By.CLASS_NAME, 'scaffold-finite-scroll__content')
    if not elements:
        print("No scroll content found.")
        return [], saved_keys

    html = await elements[0].get_attribute('innerHTML')
    soup = BeautifulSoup(html, 'html.parser')

    posts = []
    iter = 0

    for post_div in soup.select("[data-finite-scroll-hotkey-item]"):
        post_data = {}
        post_content = post_div.find('div', class_='feed-shared-inline-show-more-text')
        if not post_content:
            iter += 1
            print(f"skipped no_content {iter}\n")
            continue

        data_id = post_content.get_text(strip=True)[:35]
        if data_id == "" or data_id in saved_keys:
            iter += 1
            print(f"skipped not_a_post {iter}\n")
            continue

        profile_link = post_div.find('div', class_='update-components-actor__container')
        if not profile_link or not profile_link.find('a'):
            iter += 1
            continue

        href = profile_link.find('a').get('href')
        user = href.split("/")[3]
        slug = href.split("/")[4].split("?")[0]
        if user in blacklist or slug in blacklist:
            iter += 1
            continue

        saved_keys.add(data_id)
        post_data['profile_link'] = href
        post_data['data_id'] = data_id
        post_data['id'] = iter

        img = post_div.find('div', class_="ivm-view-attr__img-wrapper")
        img = img.find('img') if img else None
        if img:
            post_data['img_link'] = img.get('src')

        name = post_div.find('span', class_='update-components-actor__title')
        post_data['name'] = (name.find('span').get_text(strip=True)[:len(name.get_text(strip=True)) // 2]
                             if name and name.find('span') else "")

        rank = post_div.find('span', class_='update-components-actor__supplementary-actor-info')
        post_data['rank'] = rank.get_text(strip=True)[:len(rank.get_text(strip=True)) // 2] if rank else ""

        desc = post_div.find('span', class_='update-components-actor__description')
        post_data['description'] = desc.get_text(strip=True)[:len(desc.get_text(strip=True)) // 2] if desc else ""

        time_posted = post_div.find('span', class_='update-components-actor__sub-description')
        post_data['time_posted'] = time_posted.get_text(strip=True) if time_posted else ""

        print(f"name: {post_data['name']}\n")
        print(f"profile_link: {post_data['profile_link']}\n")
        print(f"rank: {post_data['rank']}\n")
        print(f"description: {post_data['description']}\n")
        print(f"time_posted: {post_data['time_posted']}\n")

        for br in post_content.find_all('br'):
            br.replace_with('\n')
        post_data['post_text'] = post_content.text[:-9]

        posts.append(post_data)
        iter += 1

    return posts, saved_keys



async def fetch_posts_person(driver, person, extension, saved_keys, blacklist=[]):
    url = f'https://www.linkedin.com/in/{person}/recent-activity/{extension}'
    await driver.get(url, wait_load=True)
    await driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    await asyncio.sleep(5.0)

    response = await driver.find_elements(By.CLASS_NAME, 'scaffold-finite-scroll__content')
    saved_keys = {''}
    if not response:
        print("Feed not found.")
        return [], saved_keys

    list = await response[0].find_element(By.XPATH, './ul[1]')
    if not response:
        print("List not found")
    inner_html = await list.get_attribute('innerHTML')

    feed_content = BeautifulSoup(inner_html, 'html.parser')

    posts = []
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
        print(post_id_elem.get('data-id', ""))
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


async def scrape_link_only(driver, approved_posts, xpath):
    links = []
    await asyncio.sleep(2.0)
    elems = await driver.find_elements(By.CLASS_NAME, "scaffold-finite-scroll__content")
    if not elems:
        print("No elems found")
        return links

    elems = await elems[0].find_elements(By.XPATH, xpath)
    print(len(elems))
    print(len(approved_posts))
    for post in approved_posts:
        index = post['id']
        elem3 = await elems[index].find_elements(By.CLASS_NAME, 'artdeco-dropdown')
        if not elem3:
            continue
        btn = await elem3[0].find_element(By.XPATH, 'button')

        if btn:
            print("YEYEYEYEYEYEYEYYEYEYEY")
            await driver.execute_script("arguments[0].click();", btn)
        else: print("ASFASQNJOGNJOGQONGQNJOQNJOGENJOQEGJONEQ+\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")

    print("Still running")
    await asyncio.sleep(2.0)

    for post in approved_posts:
        index = post['id']
        elem3 = await elems[index].find_elements(By.CLASS_NAME, 'artdeco-dropdown')
        if not elem3:
            continue

        li_elem = await elem3[0].find_elements(By.XPATH, './/ul[1]/li[2]/div[1]')
        if li_elem:
            await driver.execute_script("arguments[0].click();", li_elem[0])
            toast = await driver.find_element(By.CLASS_NAME, 'artdeco-toast-item__cta')
            p = await toast.get_attribute("href")
            post['post_link'] = p
            print(p)
            links.append(p)

    print(links)

    return links