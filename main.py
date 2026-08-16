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
    # 다운로드 완료 대기 (.crdownload 사라질 때까지)
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
            holdings_btn = wait.until(EC.element_to_be_clickable((By.XPATH, holdings_xpath)))
            driver.execute_script("arguments[0].click();", holdings_btn)
            process_downloaded_file("Holdings")
        except Exception as e:
            print(f"[알림] Holdings 다운로드 예외: {e}")

        time.sleep(3)

        # 2) Intraday Trades 다운로드 (새 탭 클릭 대응)
        try:
            driver.switch_to.window(driver.window_handles[0])
            driver.get(url)
            time.sleep(5)

            # Intraday 링크/버튼 탐색
            intraday_xpath = "//a[contains(@href, 'trade') or contains(@href, 'Trade') or contains(translate(text(), 'INTRADAY', 'intraday'), 'intraday')]"
            intraday_btn = wait.until(EC.presence_of_element_located((By.XPATH, intraday_xpath)))

            href = intraday_btn.get_attribute("href")
            if href and ".csv" in href.lower():
                driver.get(href)
            else:
                # 새 탭 생성 트리거
                driver.execute_script("arguments[0].click();", intraday_btn)

            time.sleep(3)
            # 새 탭이 열렸을 경우 해당 탭으로 전환
            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])

            process_downloaded_file("Intraday")
        except Exception as e:
            print(f"[알림] Intraday Trades 파일 미존재 또는 다운로드 불가: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_download()
