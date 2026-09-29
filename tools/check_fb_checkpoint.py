#!/usr/bin/env python3
"""
Inspect Facebook Checkpoint on Betsy Account
"""

import sys
import os
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bridge import ProxyBridge, DEFAULT_PORT

CHROMIUM_BIN = os.environ.get("CHROMIUM_PATH") or "/data/data/com.termux/files/usr/bin/chromium-browser"
CHROMEDRIVER_BIN = os.environ.get("CHROMEDRIVER_PATH") or "/data/data/com.termux/files/usr/bin/chromedriver"


def type_slowly(element, text, delay=0.03):
    for ch in text:
        element.send_keys(ch)
        time.sleep(delay)


def run_checkpoint_check():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fb_email = "betsy767@berkahkita49.biz.id"
    fb_pass = "WuzzMeta@9340!"

    bridge = ProxyBridge(local_port=DEFAULT_PORT)
    bridge.start(daemon=True)
    time.sleep(0.5)

    opts = Options()
    if os.path.exists(CHROMIUM_BIN):
        opts.binary_location = CHROMIUM_BIN
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1366,1080")
    opts.add_argument(f"--proxy-server=http://127.0.0.1:{DEFAULT_PORT}")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(executable_path=CHROMEDRIVER_BIN) if os.path.exists(CHROMEDRIVER_BIN) else None
    driver = webdriver.Chrome(service=service, options=opts)
    wait = WebDriverWait(driver, 25)

    try:
        print("[*] Navigating to https://www.facebook.com/login ...")
        driver.get("https://www.facebook.com/login/")
        time.sleep(3)

        email_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email'], input#email")))
        type_slowly(email_inp, fb_email)
        pass_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='pass'], input#pass")))
        type_slowly(pass_inp, fb_pass)
        pass_inp.send_keys(Keys.ENTER)
        time.sleep(6)

        print(f"[+] Current URL: {driver.current_url}")
        print(f"[+] Title: {driver.title}")
        driver.save_screenshot(os.path.join(base_dir, "checkpoint_step1.png"))

        # Click Continue on checkpoint if present
        continue_btns = driver.find_elements(By.XPATH, "//div[@role='button'][contains(., 'Continue')] | //button[contains(., 'Continue')]")
        if continue_btns:
            print("[+] Found 'Continue' button on checkpoint! Clicking...")
            driver.execute_script("arguments[0].click();", continue_btns[0])
            time.sleep(8)

            print(f"[+] After click URL: {driver.current_url}")
            print(f"[+] After click Title: {driver.title}")
            driver.save_screenshot(os.path.join(base_dir, "checkpoint_step2_challenge.png"))

            body = driver.find_element(By.TAG_NAME, "body").text
            print(f"[*] Page body:\n{repr(body[:500])}")

            # Iframes check (Arkose / reCAPTCHA / etc)
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print(f"[*] Iframes count: {len(iframes)}")
            for idx, ifr in enumerate(iframes):
                print(f"    [{idx}] src='{ifr.get_attribute('src')}' name='{ifr.get_attribute('name')}'")

    except Exception as e:
        print(f"[-] Error: {e}")
        driver.save_screenshot(os.path.join(base_dir, "checkpoint_error.png"))
    finally:
        driver.quit()
        bridge.stop()


if __name__ == "__main__":
    run_checkpoint_check()
