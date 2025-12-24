import os
from util import *
from selenium import webdriver
from datetime import datetime
from multiprocessing import Pool
from functools import partial
from json import dumps, dump, load
from sys import exit
from argparse import ArgumentParser
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

REPLACE_NEWLINES_WITH_SPACES = True
STATE_FOLDER = "temp/review_scraper"
DEFAULT_ANIME_PAGINATION_LIMIT = 4
DEFAULT_SCRAPE_LIMIT = 200
DEFAULT_REVIEW_PAGINATION_LIMIT = 2
MAX_WORKER_COUNT = 4
SIZE_DECIMAL_COUNT = 2
MAX_RETRY_COUNT = 3

RECOMMENDATION_SCORES = {
    "Recommended": 3,
    "Mixed Feelings": 2,
    "Not Recommended": 1
}

MONTHS_TO_INDICES = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec"
]

DEFAULT_ANIME_PAGE_URLS = [
   "https://myanimelist.net/topanime.php?type=tv",
   "https://myanimelist.net/topanime.php",
   "https://myanimelist.net/topanime.php?type=bypopularity"
]

def create_state_folder():
   if (not os.path.exists("temp")):
      os.makedirs("temp")

   folder_name = f"{STATE_FOLDER}/state_{formatted_timestamp()}"
   os.makedirs(folder_name, exist_ok=True)

   return folder_name

def save_urls(state_folder_name, urls):
   state_name = f"{state_folder_name}/urls.json"
   
   with open(state_name, "w") as f:
      dump(urls, f)

   return state_name

def to_timestamp(s: str):
    date_split = s.replace(",", "").split(" ")
    month = date_split[0]
    day = date_split[1]
    year = date_split[2]

    month_index = MONTHS_TO_INDICES.index(month) + 1

    return (int(year), month_index, int(day))

def load_source_urls(driver, source_list: list[str], scrape_limit: int, anime_pagination_limit, is_verbose: bool):
  source_wait = WebDriverWait(driver, 8)
  anime_pages_checked = set()
  anime_pages = []

  for page in source_list:
    if (len(anime_pages) >= scrape_limit):
      rich_print(f"Reached scrape limit ({scrape_limit}). Skipping...", color=ANSI_BRIGHT_YELLOW)
      break

    driver.get(page)
    source_wait.until(EC.url_to_be(page))

    for j in range(anime_pagination_limit):
      page_link_elements = driver.find_elements(By.CSS_SELECTOR, ".anime_ranking_h3 > a.hoverinfo_trigger")
      
      for link_element in page_link_elements:
        page_link = link_element.get_attribute("href")

        if (page_link in anime_pages_checked):
          continue
      
        if (len(anime_pages) >= scrape_limit):
          rich_print(f"Reached scrape limit ({scrape_limit}). Skipping {page_link}...", color=ANSI_BRIGHT_YELLOW)
          break
        
        anime_name = link_element.text
        
        anime_pages_checked.add(page_link)
        anime_pages.append(page_link + "/reviews")

        if (is_verbose):
          print(f"Adding anime page: \"{anime_name}\" ({page_link}) ({len(anime_pages)} / {scrape_limit})")
        else:
          print(f"Adding anime page: \"{anime_name}\" ({len(anime_pages)} / {scrape_limit})")
      
      cookies_prompt = driver.find_elements(By.CSS_SELECTOR, "#accept-btn")

      if (cookies_prompt):
        print("FOUND THAT PIECE OF SHIT COOKIES PROMPT. NUKING...")
        cookies_prompt[0].click()
        source_wait.until(EC.staleness_of(cookies_prompt[0]))
      
      if (j < anime_pagination_limit - 1):
        new_offset = 50 * (j + 1)
        new_url = page

        if ("?" in new_url):
          new_url += f"&limit={new_offset}"
        else:
          new_url += f"?limit={new_offset}"

        if (is_verbose):
          rich_print(f"Going to page offset {new_offset}. New URL is \"{new_url}\"", color=ANSI_BRIGHT_PURPLE)
        
        driver.get(new_url)
        source_wait.until(EC.url_to_be(new_url))
    
  return anime_pages

def scrape_pages(anime_pages, options, review_page_limit, is_verbose):
  driver = webdriver.Firefox(options=options)
  page_wait = WebDriverWait(driver, 10)

  scraped_reviews = []
  cursor = 0

  while (cursor < len(anime_pages)):
    page_url = anime_pages[cursor]

    driver.get(page_url)
    page_wait.until(EC.url_to_be(page_url))

    check_captcha(driver)

    retry_count = 0
    anime_name = page_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".title-name"))).text
    page_url = driver.current_url.rstrip("reviews")

    print(f"\n [{cursor+1} / {len(anime_pages)}] Checking reviews for anime page \"{anime_name}\"\n")

    for j in range(review_page_limit):
      try:
        check_captcha(driver)

        first_comment = page_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".review-element.js-review-element")))
        all_comments = first_comment.find_elements(By.XPATH, "following-sibling::*[contains(@class, 'review-element') and contains(@class, 'js-review-element')]")
        comments = [first_comment, *all_comments]

        rich_print(f"Found {len(comments)} comments for {anime_name} (page {j+1})", color=ANSI_YELLOW)

        for comment_idx, comment in enumerate(comments):
            username = comment.find_element(By.CSS_SELECTOR, ".username > a").text
            timestamp = to_timestamp(comment.find_element(By.CLASS_NAME, "update_at").text)
            recommendation_verdict = comment.find_element(By.CSS_SELECTOR, ".tags > .tag:first-child").text
            review_content = comment.find_element(By.CSS_SELECTOR, ".text")
            review_content_rest = review_content.find_elements(By.CSS_SELECTOR, ".js-hidden")
            user_profile_picture = comment.find_element(By.CSS_SELECTOR, ".thumb img.lazyloaded").get_attribute("src")

            review_text = review_content.text[:-3]

            if (review_content_rest):
              review_text += review_content_rest[0].get_attribute("textContent")
              
            if (REPLACE_NEWLINES_WITH_SPACES):
              review_text = review_text.replace("\n", " ")
            
            preview_content = ' '.join(review_text.split(" ")[:10]).replace("\n", "")
            
            print(f"{ANSI_BRIGHT_GREEN}{anime_name} {ANSI_BRIGHT_BLUE}[{comment_idx + 1} / {len(comments)}]{ANSI_DEFAULT} {username} ({recommendation_verdict}): \"{preview_content + (len(preview_content) < len(review_text) and "..." or "")}\"")

            scraped_reviews.append({
              'page_url': page_url,
              'anime': anime_name,
              'username': username,
              'avatar': user_profile_picture,
              'timestamp': int(datetime(timestamp[0], timestamp[1], timestamp[2]).timestamp()),
              'feelings': RECOMMENDATION_SCORES[recommendation_verdict],
              'review_text': review_text
            })
      except Exception as e:
        retry_count += 1

        if (retry_count > MAX_RETRY_COUNT):
          print(f"RETRY COUNT EXCEEDED FOR PAGE \"{page_url}\". Skipping...")
          break
          
        if (is_verbose):
          rich_print(f"\nERROR WHILE TRYING TO SCRAPE \"{page_url}\". Error: {e}. Retrying ({retry_count} / {MAX_RETRY_COUNT})...\n", color=ANSI_BRIGHT_RED)
        else:
          rich_print(f"ERROR WHILE TRYING TO SCRAPE \"{page_url}\". Retrying ({retry_count} / {MAX_RETRY_COUNT})...", color=ANSI_BRIGHT_RED)
        continue

      if (j < review_page_limit - 1):
        more_reviews_btn = driver.find_elements(By.CSS_SELECTOR, ".ga-click[data-ga-click-type=\"review-more-reviews\"]")

        if (not more_reviews_btn):
          rich_print(f"No next page for reviews found. Going to the next entry.", color=ANSI_BRIGHT_YELLOW)
          break

        next_page_url = more_reviews_btn[0].get_attribute("href")

        rich_print(f"Going to page {next_page_url}", color=ANSI_BRIGHT_YELLOW)

        driver.get(next_page_url)
        WebDriverWait(driver, 10).until(EC.url_to_be(next_page_url))
    
    cursor += 1
    
  driver.quit()
  return scraped_reviews
    
def main():
  parser = ArgumentParser(description="Scrapes the comments from MyAnimeList from a list of source urls using Selenium.", epilog="[TEST]")
  parser.add_argument("-s", "--source-urls", help="The source urls file to scrape anime pages from.")
  parser.add_argument("-o", "--output", required=True, help="Output file path.")
  parser.add_argument("-t", "--target-urls", help="An optional exported file of MAL anime pages to scrape. Will automatically append /reviews to the anime pages if it doesn't end like so. Overrides --source_urls.")
  parser.add_argument("-l", "--scrape-limit", type=int, default=DEFAULT_SCRAPE_LIMIT, help=f"The max number of anime pages to scrape. All other pages are skipped. The default value is {DEFAULT_SCRAPE_LIMIT}.")
  parser.add_argument("-p", "--pagination-limit", type=int, default=DEFAULT_ANIME_PAGINATION_LIMIT, help=f"The number of pages of anime urls to scrape from the source urls. The default value is {DEFAULT_ANIME_PAGINATION_LIMIT}.")
  parser.add_argument("-r", "--review-pagination-limit", type=int, default=DEFAULT_REVIEW_PAGINATION_LIMIT, help=f"The number of pages of reviews to scrape from the anime pages. The default value is {DEFAULT_REVIEW_PAGINATION_LIMIT}.")
  parser.add_argument("--headless", action="store_true", help="Runs the browser in headless mode.")
  parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")

  args = parser.parse_args()
  is_verbose = args.verbose

  options = Options()
  options.add_argument("--width=1280")
  options.add_argument("--height=800")

  if (args.headless):
    options.add_argument("--headless")

  if (is_verbose):
    rich_print(f"{args}", color=ANSI_BRIGHT_PURPLE)

  anime_pages = []

  if (args.target_urls):
    if (not os.path.exists(args.target_urls)):
      rich_print(f"Error: Target file \"{args.target_urls}\" not found.", color=ANSI_BRIGHT_RED)
      return 1

    if (is_verbose):
      rich_print(f"Loading target-urls {args.target_urls}", color=ANSI_BRIGHT_PURPLE)

    with open(args.target_urls, "r") as f:
      anime_pages = load(f)
    
    for i, page in enumerate(anime_pages):
      if (not page.endswith("/reviews")):
        anime_pages[i] = page.rstrip("/") + "/reviews"
    
    if (is_verbose):
      rich_print(f"Loaded target-urls: {anime_pages}", color=ANSI_BRIGHT_PURPLE)
        
  else:
    url_list = DEFAULT_ANIME_PAGE_URLS
    driver = webdriver.Firefox(options=options)
    
    if (is_verbose):
      if (args.source_urls):
        rich_print(f"Loading source-urls from file {args.source_urls}", color=ANSI_BRIGHT_PURPLE)
      else:
        rich_print(f"Loading default source-urls list: {url_list}", color=ANSI_BRIGHT_PURPLE)

    if (args.source_urls and os.path.exists(args.source_urls)):
      with open(args.source_urls, "r") as f:
        url_list = load(f)

      if (is_verbose):
        rich_print(f"Loaded source-urls {url_list}", color=ANSI_BRIGHT_PURPLE)
      
    anime_pages = load_source_urls(driver, url_list, args.scrape_limit, args.pagination_limit, is_verbose)
    driver.quit()

  rich_print(f"FOUND {len(anime_pages)} anime pages. Starting scrape...", color=ANSI_BRIGHT_BLUE)

  # cursor = 0
  # review_page_limit = args.review_pagination_limit
  scraped_reviews = []
  func = partial(scrape_pages, options=options, review_page_limit=args.review_pagination_limit, is_verbose=is_verbose)
  chunks = chunkify(anime_pages, MAX_WORKER_COUNT)

  with Pool(MAX_WORKER_COUNT) as pool:
    chunks_scraped = pool.map(func, chunks)
    scraped_reviews = [comment for chunk in chunks_scraped for comment in chunk]

  rich_print("\nExporting...", color=ANSI_BRIGHT_YELLOW)
  
  output_file_name = os.path.basename(args.output)
  serialized_json = dumps(scraped_reviews, indent=2)
  size_bytes = len(serialized_json)

  with open(args.output, "w") as f:
    f.write(serialized_json)
    rich_print(f"\nExported {output_file_name} (Size {get_size_displayable(size_bytes)})", color=ANSI_BRIGHT_GREEN)
  
  return 0

if __name__ == "__main__":
  exit_code = main()
  exit(exit_code)