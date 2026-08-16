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
            print(f"[알림] Holdings 다운로드 중 예외 발생: {e}")

        time.sleep(3)

        # 2) Intraday Trades 다운로드 (Google Sheets Export 변환 방식)
        try:
            driver.get(url)
            time.sleep(5)

            # Intraday 버튼 요소 탐색
            intraday_xpath = "//a[contains(@href, 'trade') or contains(@href, 'Trade') or contains(@href, 'intraday') or contains(@href, 'spreadsheets')]"
            intraday_elements = driver.find_elements(By.XPATH, intraday_xpath)

            sheets_url = None
            for elem in intraday_elements:
                href = elem.get_attribute("href")
                if href and ("spreadsheets" in href or "trade" in href.lower() or "intraday" in href.lower()):
                    sheets_url = href
                    break

            # 페이지 소스 내 구글 스프레드시트 ID 패턴 추적
            if not sheets_url:
                matches = re.findall(r'https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)', driver.page_source)
                if matches:
                    sheets_url = f"https://docs.google.com/spreadsheets/d/{matches[0]}/export?format=csv"

            if sheets_url:
                # 구글 시트 URL을 CSV 내보내기(Export) 주소로 직접 변환
                if "docs.google.com/spreadsheets" in sheets_url:
                    sheet_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheets_url)
                    if sheet_id_match:
                        sheet_id = sheet_id_match.group(1)
                        sheets_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

                print(f"[정보] 추출된 Intraday CSV 주소: {sheets_url}")
                res = requests.get(sheets_url, headers={"User-Agent": "Mozilla/5.0"})
                if res.status_code == 200:
                    file_path = os.path.join(DOWNLOAD_DIR, "Yieldmax_Intraday_intraday.csv")
                    with open(file_path, "wb") as f:
                        f.write(res.content)
                    process_downloaded_file("Intraday")
                else:
                    print(f"[오류] Intraday 다운로드 응답 코드 실패: {res.status_code}")
            else:
                print("[알림] Intraday 시트 주소를 찾지 못했습니다.")

        except Exception as e:
            print(f"[알림] Intraday 다운로드 예외: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_download()
