import os
import glob
import time
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
TODAY_STR = datetime.datetime.now().strftime("%Y-%m-%d")

def process_downloaded_file(label):
    for _ in range(15):
        if not glob.glob(os.path.join(DOWNLOAD_DIR, "*.crdownload")):
            break
        time.sleep(1)
    time.sleep(3)

    all_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv"))
    unprocessed_files = [f for f in all_files if not os.path.basename(f).startswith(TODAY_STR)]

    if not unprocessed_files:
        print(f"[경고] 신규 {label} CSV 파일을 찾지 못했습니다.")
        return

    latest_file = max(unprocessed_files, key=os.path.getmtime)
    original_filename = os.path.basename(latest_file)
    name_without_ext, ext = os.path.splitext(original_filename)

    new_filename = f"{TODAY_STR}_{name_without_ext}{ext}"
    new_filepath = os.path.join(DOWNLOAD_DIR, new_filename)

    os.rename(latest_file, new_filepath)
    print(f"[성공] 파일 저장 및 이름 변경 완료: {new_filename}")

def run_download():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)

    try:
        url = "https://yieldmaxetfs.com/our-etfs/ulty/"
        driver.get(url)
        time.sleep(4)

        # 1) Holdings 다운로드
        holdings_xpath = "//a[contains(@href, '.csv') and (contains(@href, 'Holdings') or contains(@href, 'holdings'))]"
        holdings_btn = wait.until(EC.presence_of_element_located((By.XPATH, holdings_xpath)))
        driver.get(holdings_btn.get_attribute("href"))
        process_downloaded_file("Holdings")

        time.sleep(3)

        # 2) Intraday 다운로드
        driver.get(url)
        time.sleep(3)
        trades_xpath = "//a[contains(@href, '.csv') and (contains(@href, 'trades') or contains(@href, 'Trades'))]"
        intraday_btn = wait.until(EC.presence_of_element_located((By.XPATH, trades_xpath)))
        driver.get(intraday_btn.get_attribute("href"))
        process_downloaded_file("Intraday")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_download()
