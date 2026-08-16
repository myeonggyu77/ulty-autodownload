import os
import glob
import time
import re
import datetime
import requests
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
        print(f"[알림] 신규 {label} CSV 파일이 없습니다.")
        return False

    latest_file = max(unprocessed_files, key=os.path.getmtime)
    original_filename = os.path.basename(latest_file)
    name_without_ext, ext = os.path.splitext(original_filename)

    new_filename = f"{TODAY_STR}_{name_without_ext}{ext}"
    new_filepath = os.path.join(DOWNLOAD_DIR, new_filename)

    os.rename(latest_file, new_filepath)
    print(f"[성공] {label} 파일 저장 완료: {new_filename}")
    return True

def run_download():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 15)

    try:
        url = "https://yieldmaxetfs.com/our-etfs/ulty/"
        driver.get(url)
        time.sleep(5)

        # 1) Holdings 다운로드
        try:
            holdings_xpath = "//a[contains(@href, '.csv') and (contains(@href, 'Holdings') or contains(@href, 'holdings'))]"
            holdings_btn = wait.until(EC.presence_of_element_located((By.XPATH, holdings_xpath)))
            driver.get(holdings_btn.get_attribute("href"))
            process_downloaded_file("Holdings")
        except Exception as e:
            print(f"[알림] Holdings 다운로드 실패: {e}")

        time.sleep(3)

        # 2) Intraday Trades 다운로드 (전체 소스 및 iframe 탐색 방식)
        try:
            driver.get(url)
            time.sleep(5)

            csv_url = None
            page_source = driver.page_source

            # 소스 코드 전체에서 intraday/trade 관련 csv 링크 정규식 탐색
            csv_matches = re.findall(r'https?://[^\s"\']*?(?:trade|intraday)[^\s"\']*?\.csv', page_source, re.IGNORECASE)
            
            if csv_matches:
                csv_url = csv_matches[0]
            else:
                # iframe 내부도 체크
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    iframe_src = iframe.get_attribute("src")
                    if iframe_src and ("trade" in iframe_src.lower() or "intraday" in iframe_src.lower()):
                        driver.get(iframe_src)
                        time.sleep(3)
                        iframe_source = driver.page_source
                        matches = re.findall(r'https?://[^\s"\']*?\.csv', iframe_source, re.IGNORECASE)
                        if matches:
                            csv_url = matches[0]
                            break

            if csv_url:
                print(f"[정보] Intraday CSV URL 발견: {csv_url}")
                response = requests.get(csv_url, headers={"User-Agent": "Mozilla/5.0"})
                if response.status_code == 200:
                    target_path = os.path.join(DOWNLOAD_DIR, "Yieldmax_Intraday_intraday.csv")
                    with open(target_path, "wb") as f:
                        f.write(response.content)
                    process_downloaded_file("Intraday")
                else:
                    print(f"[오류] Intraday CSV 직접 다운로드 실패 (상태 코드: {response.status_code})")
            else:
                print("[알림] Intraday CSV 링크를 소스에서 직접 찾지 못했습니다.")

        except Exception as e:
            print(f"[알림] Intraday 처리 중 예외 발생: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_download()
