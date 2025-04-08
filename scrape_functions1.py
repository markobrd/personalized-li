import asyncio
from bs4 import BeautifulSoup
import time
import json

from playwright.async_api import async_playwright,Page

# Utility to scroll and wait
async def scroll_page(page, steps=3, wait_time=2):
    for _ in range(steps):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight, {behavior:'smooth'});")
        await asyncio.sleep(wait_time)
    await page.evaluate("window.scrollTo(0, 0);")


async def fetch_posts(page, saved_keys, blacklist=[]):
    await scroll_page(page)

    content = await page.inner_html('.scaffold-finite-scroll__content')
    soup = BeautifulSoup(content, 'html.parser')

    posts = []
    iter = 0

    for post_div in soup.select("[data-finite-scroll-hotkey-item]"):
        post_data = {}

        post_content = post_div.find('div', class_='feed-shared-inline-show-more-text')
        if not post_content:
            iter += 1
            print("skipped no_content", iter)
            continue

        data_id = post_content.get_text(strip=True)[:35]
        if data_id == "" or len(post_div.get('data-id', "")) > 35 or (data_id in saved_keys):
            iter += 1
            print("skipped not_a_post", iter)
            continue

        profile_link_div = post_div.find('div', class_='update-components-actor__container')
        if not profile_link_div:
            iter += 1
            continue

        profile_link_tag = profile_link_div.find('a')
        if not profile_link_tag:
            iter += 1
            continue

        profile_href_parts = profile_link_tag.get('href').split("/")
        if (profile_href_parts[3] in blacklist) or (profile_href_parts[4].split("?")[0] in blacklist):
            iter += 1
            continue

        saved_keys.add(data_id)
        post_data['embeding_url'] = post_div.get('data-id')
        post_data['profile_link'] = profile_link_tag.get('href')
        post_data['data_id'] = data_id
        post_data['id'] = iter

        img = post_div.find_all('div', class_="ivm-view-attr__img-wrapper")
        if img and img[-1].find('img'):
            post_data['img_link'] = img[-1].find('img').get('src')

        name = post_div.find('span', class_='update-components-actor__title')
        post_data['name'] = name.find('span').get_text(strip=True)[:len(name)//2] if name else ""

        rank = post_div.find('span', class_='update-components-actor__supplementary-actor-info')
        post_data['rank'] = rank.get_text(strip=True)[:len(rank)//2] if rank else ""

        desc = post_div.find('span', class_='update-components-actor__description')
        post_data['description'] = desc.get_text(strip=True)[:len(desc)//2] if desc else ""

        time_posted = post_div.find('span', class_='update-components-actor__sub-description')
        post_data['time_posted'] = time_posted.get_text(strip=True) if time_posted else ""

        for br in post_content.find_all('br'):
            br.replace_with('\n')

        post_data['post_text'] = post_content.text[:-9]
        posts.append(post_data)
        iter += 1

    return posts, saved_keys


async def fetch_posts_person(page, person, extension, saved_keys, blacklist=[]):
    await scroll_page(page)
    print("Scrapping " + person + " " + extension)
    await asyncio.sleep(2.0)
    html = await page.inner_html('.scaffold-finite-scroll__content ul')
    soup = BeautifulSoup(html, 'html.parser')

    posts = []
    iter = 0

    for post_div in soup.find_all("li", recursive=False):
        post_data = {}

        content = post_div.find("span", class_="break-words tvm-parent-container")
        if not content:
            iter += 1
            continue

        post_id_elem = post_div.find_all('div', class_="feed-shared-update-v2")[0]
        data_id = content.text.strip()[:35]
        if (data_id in saved_keys) or len(post_id_elem.get('data-id', "")) > 35:
            iter += 1
            print("skipped no_content", iter)
            continue

        profile_link_div = post_div.find('div', class_='update-components-actor__container')
        if not profile_link_div:
            iter += 1
            print("skipped not_a_post", iter)
            continue

        profile_link_tag = profile_link_div.find('a')
        if not profile_link_tag:
            iter += 1
            continue

        profile_href_parts = profile_link_tag.get('href').split("/")
        if (profile_href_parts[3] in blacklist) or (profile_href_parts[4].split("?")[0] in blacklist):
            iter += 1
            continue

        saved_keys.add(data_id)
        post_data['profile_link'] = profile_link_tag.get('href')

        for br in content.find_all('br'):
            br.replace_with('\n')

        if post_div.find("div", class_ = "feed-shared-update-v2"):
            data_urn_div = post_div.find("div", class_ = "feed-shared-update-v2")
            post_data['embeding_url'] = data_urn_div.get("data-urn")
        post_data['post_text'] = content.text[:-9]
        post_data['data_id'] = data_id
        post_data['id'] = iter

        img = post_div.find_all('div', class_="ivm-view-attr__img-wrapper")
        if img and img[-1].find('img'):
            post_data['img_link'] = img[-1].find('img').get('src')

        name = post_div.find('span', class_='update-components-actor__title')
        post_data['name'] = name.find('span').get_text(strip=True) if name else ""

        rank = post_div.find('span', class_='update-components-actor__supplementary-actor-info')
        post_data['rank'] = rank.get_text(strip=True) if rank else ""

        desc = post_div.find('span', class_='update-components-actor__description')
        post_data['description'] = desc.get_text(strip=True)[:len(desc)//2] if desc else ""

        time_posted = post_div.find('span', class_='update-components-actor__sub-description')
        post_data['time_posted'] = time_posted.get_text(strip=True) if time_posted else ""

        posts.append(post_data)
        iter += 1

    return posts, saved_keys


async def scrape_link_only(page: Page, approved_posts, xpath):
    links = []
    print("Posts: \n\n")

    # Wait for the scroll container to be present
    await page.wait_for_selector(".scaffold-finite-scroll__content",timeout=10000 )
    container = page.locator(".scaffold-finite-scroll__content")

    # Use locator with XPath
    elems = container.locator(f":scope >> xpath={xpath}")
    elem_count = await elems.count()
    print(elem_count)
    await asyncio.sleep(1.0)

    # First round: Click dropdown buttons
    for post in approved_posts:
        index = post['id']
        if index >= elem_count:
            print("out of bounds")
            continue

        elem = elems.nth(index)
        dropdowns = elem.locator(".artdeco-dropdown")
        has_dropdown = await dropdowns.count()

        if not has_dropdown:
            print("no dropdowns")
            continue

        button = dropdowns.locator("button")
        if await button.count():
            await button.first.click(force=True)


            # Target element using relative XPath
            #await dropdowns.wait_for_selector("xpath=.//ul/li[2]/div",timeout=10000 )
            target_elem = dropdowns.locator("xpath=.//ul/li[2]/div")
            await target_elem.wait_for(state="visible")
            if await target_elem.count():
                await target_elem.first.click(force=True)
                
                # Wait for the toast notification and get link
                await page.wait_for_selector(".artdeco-toast-item__cta", timeout=3000)
                link = page.locator(".artdeco-toast-item__cta")
                if await link.count():
                    href = await link.first.get_attribute("href")
                    post['post_link'] = href
                    links.append(href)
                else:
                    print("No link found")
            else:
                print("Invalid xpath")
        else:
            print("No button ;(... \n\n\n")

    print(links)
    return links