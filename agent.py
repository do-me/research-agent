from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import os
import time
import random
import requests
import glob
from tqdm import tqdm 
import math 

approximate_results_rounded_up = 19
user_query = "semantic search"
scihub_base = "" 

def get_scholar_urls(query, start_index=0):
    """Retrieves URLs from Google Scholar search results."""
    base_url = f"https://scholar.google.com/scholar?start={start_index}&q=earth"
    url = base_url + query.replace(" ", "+")

    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        urls = [link.get('href') for h3 in soup.find_all('h3', class_='gs_rt') if (link := h3.find('a'))]
        return urls

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

print("Mining Google Scholar URLs...")
all_urls = []
for i in tqdm(list(range(0, math.ceil(approximate_results_rounded_up / 10) * 10 + 10, 10))):
    urls = get_scholar_urls(user_query, i)
    print(urls)
    all_urls.append(urls)
    if len(urls) == 0:
        break
    time.sleep(5)

all_urls = list(set([url for url_list in all_urls for url in url_list])) # flatten
print("Mining Google Scholar URLs finished")

def random_user_agent():
    """Returns a random user agent string."""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        # ... Add more user agents
    ]
    return random.choice(user_agents)


def get_latest_downloaded_file(download_dir, start_time):
    """Finds the latest downloaded file in the directory."""
    list_of_files = glob.glob(os.path.join(download_dir, '*'))
    if not list_of_files:
        return None
    latest_file = max(list_of_files, key=os.path.getctime)
    return os.path.basename(latest_file) if os.path.getctime(latest_file) >= start_time else None


def download_pdf_from_scihub(urls, download_dir):
    """Downloads PDFs from Sci-Hub."""

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    prefs = {"download.default_directory": download_dir}
    options.add_experimental_option("prefs", prefs)

    start_time = time.time()
    downloaded_count = 0
    downloaded_files = []
    citations = []

    with webdriver.Chrome(options=options) as driver:
        for url in urls:
            try:
                options.add_argument(f"user-agent={random_user_agent()}")
                driver.get(scihub_base + url)

      
                if "404 Not Found" in driver.page_source or "Unfortunately" in driver.page_source:
                    print(f"Skipping {url} - Not found (404 or similar).")
                    continue

                # Consolidated wait for download button or DDoS protection elements.
                try:
                    WebDriverWait(driver, 25).until(  # Increased timeout for combined wait
                        EC.any_of(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "#buttons button[onclick]")),
                            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'DDoS-Guard')]")),
                        )
                    )

                    if "DDoS-Guard" in driver.page_source: # Handle DDoS if present
                        print("DDoS protection detected. Waiting...")
                        WebDriverWait(driver, 20).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "#buttons button[onclick]"))
                        )
                        print("DDoS protection passed.")


                    download_button = driver.find_element(By.CSS_SELECTOR, "#buttons button[onclick]")
                    download_button.click()
                    print(f"Download initiated for {url}")
                    downloaded_count += 1

                    try:
                        citation_element = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.ID, "citation"))
                        )
                        citations.append(citation_element.text.strip())

                        latest_file = get_latest_downloaded_file(download_dir, start_time)
                        if latest_file:
                            downloaded_files.append(latest_file.replace(".crdownload", ""))
                            print(f"Downloaded {latest_file} for {url}")

                    except TimeoutException:
                        print(f"Citation or file not found for {url}")


                except TimeoutException:
                    print(f"Download button or DDoS protection not found/timed out for {url}")

            except Exception as e:
                print(f"Error processing {url}: {e}")

    end_time = time.time()
    elapsed_time = end_time - start_time
    average_time = elapsed_time / len(urls) if urls else 0

    print(f"\nDownloaded {downloaded_count}/{len(urls)} documents")
    print(f"Average time per document: {average_time:.2f} seconds")
    print("Following documents have been downloaded:")
    for citation in citations:
        print(citation)
    print(downloaded_files)

download_pdf_from_scihub(all_urls, download_dir="/Users/dome/downloads/test")
