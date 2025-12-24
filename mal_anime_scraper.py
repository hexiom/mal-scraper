import os
from util import *
from argparse import ArgumentParser
from selenium import webdriver
from multiprocessing import Pool
from functools import partial
from json import load, dump, dumps
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

ASYNC_WORKER_COUNT = 4
REVIEWS_MAX_PAGES = 4
STATE_FOLDER = "temp/anime_details"
STORE_NUMBERS_AS_STRINGS = False

def create_state_folder():
   if (not os.path.exists("temp")):
      os.makedirs("temp")

   folder_name = f"{STATE_FOLDER}/state_{formatted_timestamp()}"
   os.makedirs(folder_name, exist_ok=True)

   return folder_name

def default_options():
   options = Options()
   options.add_argument("--width=1280")
   options.add_argument("--height=800")
   return options

def save_urls(state_folder_name, urls):
   state_name = f"{state_folder_name}/urls.json"
   
   with open(state_name, "w") as f:
      dump(urls, f)

   return state_name

def scrape_details(chunk, is_verbose: bool):
   driver = webdriver.Firefox(options=default_options())
   page_wait = WebDriverWait(driver, 5)
   cursor = 0
   retry_count = 0

   scraped_anime_data = []
   
   while (cursor < len(chunk)):
      anime_page = chunk[cursor]

      try:
         driver.get(anime_page)
         page_wait.until(EC.url_to_be(anime_page))

         if (is_verbose):
            rich_print(f"URL CHANGED DETECTED: {anime_page}", color=ANSI_BRIGHT_PURPLE)

         anime_name = page_wait.until(EC.presence_of_element_located((By.CLASS_NAME, "title-name"))).text
         secondary_title = driver.find_elements(By.CLASS_NAME, "title-english")
         anime_image = driver.find_elements(By.CSS_SELECTOR, ".leftside img.lazyloaded")
         score_review_count = driver.find_element(By.CLASS_NAME, "score").get_attribute("data-user").split(" ")[0]
         score = driver.find_element(By.CLASS_NAME, "score-label").text
         anime_rank = driver.find_element(By.CSS_SELECTOR, ".numbers.ranked").text[8:]
         anime_popularity = driver.find_element(By.CSS_SELECTOR, ".numbers.popularity").text[12:]
         anime_numbers = driver.find_element(By.CSS_SELECTOR, ".numbers.members").text[8:]
         synopsis = driver.find_element(By.CSS_SELECTOR, "p[itemprop=\"description\"]").text.replace("\n", " ").replace("[Written by MAL Rewrite]", "")
         anime_genres = map(lambda e: e.get_attribute("textContent"), driver.find_elements(By.CSS_SELECTOR, "span[itemprop=\"genre\"]"))

         if (secondary_title):
            secondary_title = secondary_title[0].text
         else:
            secondary_title = None
         
         anime_image = (anime_image and anime_image[0].get_attribute("src") or "")
      except Exception as e:
         retry_count += 1

         if (retry_count >= 3):
            retry_count = 0
            cursor += 1
            rich_print(f"RETRY COUNT REACHED FOR PAGE \"{anime_page}\". Skipping...", color=ANSI_BRIGHT_YELLOW)
         else:
            if (is_verbose):
               rich_print(f"ERROR FACED WHILE PARSING \"{anime_page}\": \"{e}\". Retrying...", color=ANSI_BRIGHT_YELLOW)
            else:
               rich_print(f"ERROR FACED WHILE PARSING \"{anime_page}\". Retrying...", color=ANSI_BRIGHT_YELLOW)

         continue
         
      rich_print(f"[{cursor + 1} / {len(chunk)}] {anime_name} ({score} @ {score_review_count} reviews) #{anime_rank}", color=ANSI_BRIGHT_BLUE, bold=True)

      if (not STORE_NUMBERS_AS_STRINGS):
         score = float(score)
         score_review_count = int(score_review_count.replace(",", ""))
         anime_numbers = int(anime_numbers.replace(",", ""))
         anime_rank = int(anime_rank.replace(",", ""))
         anime_popularity = int(anime_popularity.replace(",", ""))

      scraped_anime_data.append({
         "anime": anime_name,
         "english_name": secondary_title,
         "cover": anime_image,
         "anime_url": anime_page,
         "score": score,
         "reviews": score_review_count,
         "members": anime_numbers,
         "ranking": anime_rank,
         "popularity": anime_popularity,
         "synopsis": synopsis,
         "genres": list(anime_genres)
      })

      retry_count = 0
      cursor += 1
   
   driver.quit()
   return scraped_anime_data

def main():
   parser = ArgumentParser(description="Scrapes anime details from MyAnimeList given a list of scraped comments or a list of anime urls using Selenium.", epilog="[TEST]")
   parser.add_argument("input_file", nargs="?", help="The scraped MAL comments file to extract the anime urls from.")
   parser.add_argument("-o", "--output", required=True, help="Output file path.")
   parser.add_argument("-u", "--urls", help="An optional exported file of MAL urls to scrape. Overrides input file.")
   parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")

   args = parser.parse_args()
   is_verbose = args.verbose

   if (not args.urls and not args.input_file):
      rich_print("ERROR: Input file or url list (-u) not specified.", color=ANSI_BRIGHT_RED)
      return
   elif (not args.urls and args.input_file and not os.path.exists(args.input_file)):
      rich_print("ERROR: Input file specified does not exist.", color=ANSI_BRIGHT_RED)
      return
   elif (not args.input_file and args.urls and not os.path.exists(args.urls)):
      rich_print("ERROR: URL file specified does not exist.", color=ANSI_BRIGHT_RED)
      return

   state_folder_name = create_state_folder()
   
   unique_anime_pages = []

   if (is_verbose):
      rich_print(f"{args}", color=ANSI_BRIGHT_PURPLE)

   if (args.urls):
      try:
         with open(args.urls, "r") as f:
            unique_anime_pages = load(f, encoding="utf-8")
      except Exception as e:
         rich_print("Error while parsing URL file. Corrupted or invalid file.", color=ANSI_BRIGHT_RED)
   else:
      with open(args.input_file, "r") as f:
         scraped_data = load(f)

         for comment in scraped_data:
            if (comment["page_url"] not in unique_anime_pages):
               unique_anime_pages.append(comment["page_url"])

      save_urls(state_folder_name, unique_anime_pages)
   
   rich_print(f"FOUND {len(unique_anime_pages)} anime pages to scrape.", color=ANSI_BRIGHT_YELLOW)
   
   scraped_anime_data = []
   func = partial(scrape_details, is_verbose=is_verbose)
   chunks = chunkify(unique_anime_pages, ASYNC_WORKER_COUNT)

   with Pool(ASYNC_WORKER_COUNT) as pool:
      scraped_anime_data = pool.map(func, chunks)

   rich_print(f"\nExporting...", color=ANSI_BRIGHT_YELLOW)
   
   file_name = os.path.basename(args.output)
   serialized_json = dumps(scraped_anime_data, indent=2)
   size_bytes = len(serialized_json)
   
   with open(args.output, "w") as f:
      f.write(serialized_json)

   rich_print(f"\nExported {file_name} (Size {get_size_displayable(size_bytes)})", color=ANSI_BRIGHT_GREEN)

if __name__ == "__main__":
   main()