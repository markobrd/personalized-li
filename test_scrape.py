import asyncio
import arsenic
import random
import logging
import os
from arsenic import services, browsers, sessions
import yaml
import Keys

# --- Configuration (MUST BE MODIFIED) ---
TARGET_LOGIN_URL = "https://linkedin.com/login" # REPLACE
# !! IMPORTANT: Use secure methods like environment variables for credentials !!
with open('config.yaml') as config_file:
    config = yaml.safe_load(config_file)

# Configuration
USERNAME = config['credentials']['username']
PASSWORD = config['credentials']['password']

# List of URLs on the target site to scrape AFTER logging in
URLS_TO_SCRAPE = [
    "https://website.com/profile/user1", # REPLACE with actual target page URLs
    "https://website.com/data/item/abc",
    "https://website.com/details/page/456",
    "https://website.com/profile/user2",
    "https://website.com/data/item/def",
    "https://website.com/details/page/789",
    # Add many more URLs as needed
]

MAX_CONCURRENT_SESSIONS = 3 # Limit simultaneous browser sessions
POLITE_DELAY_SECONDS_MIN = 2
POLITE_DELAY_SECONDS_MAX = 5

# --- Logging Setup (Better for Async) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Arsenic Service and Browser Configuration ---
# Example using Chromedriver; adapt for Geckodriver if using Firefox
SERVICE = services.Chromedriver()
# Find chromedriver automatically, or specify path:
# SERVICE = services.Chromedriver(binary='/path/to/chromedriver')

BROWSER = browsers.Chrome(
    # Add Chrome options if needed, similar to Selenium's ChromeOptions
    **{
        "goog:chromeOptions": {
            "args": [
                "--headless", # Run headless if desired (may increase detection risk)
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--log-level=3",
            ]
        }
    }
)

# --- Coroutines ---

async def perform_login(session: sessions.Session, worker_name: str):
    """Logs into the website using arsenic session. Adapt selectors!"""
    try:
        await session.get(TARGET_LOGIN_URL)
        log.info(f"[{worker_name}] Navigated to login page.")

        # --- Adapt these selectors for the target website (use CSS or XPath) ---
        user_field = await session.wait_for_element(5, "#username") # REPLACE CSS selector
        pass_field = await session.get_element("#password") # REPLACE CSS selector

        # ---

        await user_field.send_keys(USERNAME)
        await pass_field.send_keys(PASSWORD)
        log.info(f"[{worker_name}] Credentials entered.")
        pass_field.send_keys(Keys.RETURN)

        # --- Add a check to confirm login was successful ---
        # Example: Wait for an element that only appears after login
        await session.wait_for_element(10, "#user_dashboard_element_id") # REPLACE CSS selector
        log.info(f"[{worker_name}] Login successful.")
        return True

    except Exception as e:
        log.error(f"[{worker_name}] Login failed: {e}", exc_info=True)
        return False

async def scrape_page_data(session: sessions.Session, url: str, worker_name: str):
    """Navigates to a URL and scrapes data. Adapt selectors and logic!"""
    try:
        await session.get(url)
        log.info(f"[{worker_name}] Navigated to {url}")

        # --- Adapt data extraction logic for the target website ---
        # Example: Get the page title and a specific element's text
        await session.wait_for_element(5, "body") # Wait for basic page structure
        page_title = await session.get_title()
        data_element = await session.get_element(".important-data-class") # REPLACE SELECTOR
        scraped_data = await data_element.get_text()
        # ---

        log.info(f"[{worker_name}] Scraped data from {url}: Title='{page_title}', Data='{scraped_data[:30]}...'")
        return {"url": url, "title": page_title, "data": scraped_data} # Return collected data

    except Exception as e:
        log.error(f"[{worker_name}] Failed to scrape {url}: {e}", exc_info=True)
        return {"url": url, "error": str(e)} # Return error information

async def worker(name: str, url_queue: asyncio.Queue, results_list: list, semaphore: asyncio.Semaphore):
    """Async worker task that manages a browser session."""
    log.info(f"[{name}] Worker starting...")
    service = None
    session = None

    # Limit concurrent browser instances using the semaphore
    async with semaphore:
        log.info(f"[{name}] Acquired semaphore, starting browser...")
        try:
            # Start webdriver service and browser session for this worker
            service = SERVICE # Use the configured service
            async with arsenic.start_session(service, BROWSER) as session:
                log.info(f"[{name}] Browser session started.")

                # Log in once for this session
                if not await perform_login(session, name):
                    log.warning(f"[{name}] Exiting due to login failure.")
                    return # Stop this worker

                while not url_queue.empty():
                    current_url = await url_queue.get()
                    log.info(f"[{name}] Got URL from queue: {current_url}")

                    # Scrape the page
                    result = await scrape_page_data(session, current_url, name)
                    results_list.append(result) # Append result

                    # Mark task as done in the url_queue
                    url_queue.task_done()
                    log.info(f"[{name}] Finished processing {current_url}")

                    # --- Polite non-blocking delay ---
                    delay = random.uniform(POLITE_DELAY_SECONDS_MIN, POLITE_DELAY_SECONDS_MAX)
                    log.info(f"[{name}] Waiting for {delay:.2f} seconds...")
                    await asyncio.sleep(delay) # Use asyncio.sleep!

        except Exception as e:
            log.error(f"[{name}] An error occurred in worker: {e}", exc_info=True)
        finally:
            # Session is closed automatically by 'async with'
            # Service needs explicit stopping if not managed elsewhere, but
            # arsenic's context manager might handle it. Check docs if unsure.
            # If service were started manually:
            # if service and service.process: await service.stop()
            log.info(f"[{name}] Worker finished or encountered error.")


async def main():
    """Main coroutine to set up and run workers."""
    start_time = asyncio.get_event_loop().time()

    url_queue = asyncio.Queue()
    for url in URLS_TO_SCRAPE:
        url_queue.put_nowait(url)

    results_list = [] # Simple list for results
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SESSIONS)

    log.info(f"Starting {MAX_CONCURRENT_SESSIONS} worker tasks concurrently...")
    tasks = []
    for i in range(MAX_CONCURRENT_SESSIONS): # Create worker tasks up to the limit
        task = asyncio.create_task(
            worker(f"Worker-{i+1}", url_queue, results_list, semaphore),
            name=f"WorkerTask-{i+1}" # Optional: Name the task itself
        )
        tasks.append(task)

    # Wait for the queue to be fully processed
    await url_queue.join()
    log.info("All URLs have been processed by workers.")

    # Optionally, wait for worker tasks to fully complete (including final delays/cleanup)
    # This might not be strictly necessary if queue.join() is sufficient guarantee
    # but can be useful for cleaner shutdown.
    # await asyncio.gather(*tasks, return_exceptions=True) # Wait for tasks if needed

    # Or, to ensure tasks stop after queue is empty (alternative to gather):
    # You could add sentinel values to queue or cancel tasks.
    # For simplicity, we rely on queue.join() and tasks finishing naturally.

    end_time = asyncio.get_event_loop().time()
    log.info(f"\n--- Scraping Complete ---")
    log.info(f"Processed {len(URLS_TO_SCRAPE)} URLs.")
    log.info(f"Collected {len(results_list)} results.")
    log.info(f"Total time: {end_time - start_time:.2f} seconds.")

    # Process or save final_results as needed
    # log.info("\nSample Results:")
    # for res in results_list[:5]:
    #     log.info(res)

# --- Run the Async Event Loop ---
if __name__ == "__main__":
    # On Windows, default event loop policy might cause issues with subprocesses
    # Uncomment if needed:
    # if os.name == 'nt':
    #    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())