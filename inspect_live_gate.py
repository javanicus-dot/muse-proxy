#!/usr/bin/env python3
"""
Inspect Confirm Age on Live Session of Muse.ai
Runs registration directly to stay inside the authenticated browser context.
"""

import sys
import os
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tempmail_api import BerkahTempMail
from bridge import ProxyBridge, DEFAULT_PORT

CHROMIUM_BIN = os.environ.get("CHROMIUM_PATH") or "/data/data/com.termux/files/usr/bin/chromium-browser"
CHROMEDRIVER_BIN = os.environ.get("CHROMEDRIVER_PATH") or "/data/data/com.termux/files/usr/bin/chromedriver"


def type_slowly(element, text, delay=0.03):
    for ch in text:
        element.send_keys(ch)
        time.sleep(delay)


def run_test():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tm = BerkahTempMail()
    inbox = tm.create_inbox()
    email = inbox["address"]
    session_token = inbox["session"]
    print(f"[+] TempMail Generated : {email}")

    bridge = ProxyBridge(local_port=DEFAULT_PORT)
    bridge.start(daemon=True)
    time.sleep(0.5)

    opts = Options()
    if os.path.exists(CHROMIUM_BIN):
        opts.binary_location = CHROMIUM_BIN
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1366,1080")
    opts.add_argument(f"--proxy-server=http://127.0.0.1:{DEFAULT_PORT}")
    opts.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(executable_path=CHROMEDRIVER_BIN) if os.path.exists(CHROMEDRIVER_BIN) else None
    driver = webdriver.Chrome(service=service, options=opts)
    wait = WebDriverWait(driver, 25)

    try:
        driver.get("https://muse.ai")
        time.sleep(3)

        email_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Mobile number or email'], input[inputmode='email']")))
        email_inp.clear()
        type_slowly(email_inp, email)
        time.sleep(0.5)

        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", submit_btn)

        otp_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[maxlength='6']")))
        code, _ = tm.wait_for_code(email, session=session_token, timeout=45)
        type_slowly(otp_inp, code, delay=0.05)
        time.sleep(1)

        # Birthday setup
        year_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Year']")))
        driver.execute_script("arguments[0].click();", year_btn)
        time.sleep(0.5)
        opt_year = [o for o in driver.find_elements(By.CSS_SELECTOR, "[role='option']") if o.text.strip() == "1998"]
        if opt_year:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", opt_year[0])
        time.sleep(0.5)

        month_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Month']")
        driver.execute_script("arguments[0].click();", month_btn)
        time.sleep(0.5)
        opt_month = [o for o in driver.find_elements(By.CSS_SELECTOR, "[role='option']") if o.text.strip() == "May"]
        if opt_month:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", opt_month[0])
        time.sleep(0.5)

        confirm_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
        driver.execute_script("arguments[0].click();", confirm_btn)
        print("[+] Birthday submitted.")
        time.sleep(8)

        # Disclosure step
        print(f"[+] Reached: {driver.current_url}")
        get_started_btn = None
        for b in driver.find_elements(By.TAG_NAME, "button"):
            if "get started" in b.text.strip().lower():
                get_started_btn = b
                break

        if get_started_btn:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", get_started_btn)
            print("[+] Clicked Get Started.")
            time.sleep(6)

        print(f"[+] Landed on: {driver.current_url}")
        driver.save_screenshot(os.path.join(base_dir, "live_verification_screen.png"))

        # Now test clicking 'Confirm age'
        confirm_age_btn = None
        for b in driver.find_elements(By.TAG_NAME, "button"):
            if "confirm age" in b.text.strip().lower():
                confirm_age_btn = b
                break

        if confirm_age_btn:
            print("[+] Found 'Confirm age' button! Clicking...")
            driver.execute_script("arguments[0].click();", confirm_age_btn)
            time.sleep(6)

            print(f"[+] After Confirm age URL: {driver.current_url}")
            print(f"[+] After Confirm age Title: {driver.title}")
            driver.save_screenshot(os.path.join(base_dir, "after_confirm_age_click.png"))

            # Check if Stripe or Meta Pay elements exist
            body_text = driver.find_element(By.TAG_NAME, "body").text
            print(f"[*] Body preview:\n{repr(body_text[:400])}")

            # Check iframes
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print(f"[*] Iframes count: {len(iframes)}")
            for idx, ifr in enumerate(iframes):
                print(f"    [{idx}] src='{ifr.get_attribute('src')}' name='{ifr.get_attribute('name')}'")

    except Exception as e:
        print(f"[-] Error: {e}", file=sys.stderr)
        driver.save_screenshot(os.path.join(base_dir, "test_error.png"))
    finally:
        driver.quit()
        bridge.stop()


if __name__ == "__main__":
    run_test()
