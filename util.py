from datetime import datetime
from math import log10
from selenium.webdriver.common.by import By
from time import sleep

ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_BLUE = "\033[34m"
ANSI_PURPLE = "\033[35m"
ANSI_CYAN = "\033[36m"

ANSI_BRIGHT_RED = "\033[91m"
ANSI_BRIGHT_GREEN = "\033[92m"
ANSI_BRIGHT_YELLOW = "\033[93m"
ANSI_BRIGHT_BLUE = "\033[94m"
ANSI_BRIGHT_PURPLE = "\033[95m"
ANSI_BRIGHT_CYAN = "\033[96m"

ANSI_DEFAULT = "\033[0m"

ANSI_BOLD = "\033[1m"
ANSI_UNDERLINE = "\033[4m"

def formatted_timestamp():
   return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def rich_print(*values, color=ANSI_DEFAULT, bold=False, underline=False):
  text = ' '.join([str(v) for v in values])

  style = ''

  if (bold):
    style += ANSI_BOLD

  if (underline):
    style += ANSI_UNDERLINE

  style += color

  print(f"{style}{text}{ANSI_DEFAULT}")

def check_captcha(driver):
  captcha_container = driver.find_elements(By.ID, "captcha-container")

  if (captcha_container):
    rich_print("Captcha found. Waiting for user input...", color=ANSI_BRIGHT_YELLOW)

  while True:
    sleep(1)
    if (not driver.find_elements(By.ID, "captcha-container") and not driver.find_elements(By.CLASS_NAME, "amzn-captcha-modal")):
      break
  
def chunkify(lst, n):
    """Split lst into n roughly equal chunks"""
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m):(i+1)*k + min(i+1, m)] for i in range(n)]

def get_size_displayable(size_bytes: int, decimal_count=2) -> str:
  size_abbreviations = {
    0: "B",
    3: "KB",
    6: "MB",
    9: "GB"
  }

  n_log = int(log10(size_bytes))
  pow_10 = max(k for k in size_abbreviations.keys() if k <= n_log)
    
  return f"{(size_bytes / pow(10, pow_10)):.{decimal_count}f} {size_abbreviations[pow_10]}"
    