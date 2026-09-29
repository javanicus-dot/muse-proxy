#!/usr/bin/env python3
"""
Muse.ai Automated Signup / Login with TempMail CF and RainProxy US
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

# Add tempmail-cf client to path
sys.path.insert(0, "/data/data/com.termux/files/home/tempmail-cf")
from client import TempMailClient

from bridge import ProxyBridge, DEFAULT_PORT

CHROMIUM_BIN = os.environ.get("CHROMIUM_PATH") or "/data/data/com.termux/files/usr/bin/chromium-browser"
CHROMEDRIVER_BIN = os.environ.get("CHROMEDRIVER_PATH") or "/data/data/com.termux/files/usr/bin/chromedriver"


def run_signup():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    step1_png = os.path.join(base_dir, "step1_input.png")
    step2_png = os.path.join(base_dir, "step2_after_continue.png")
    log_file = os.path.join(base_dir, "signup_session.json")

    print("=" * 60)
    print("  MUSE.AI SIGNUP ENGINE (TEMPMAIL CF + RAINPROXY US)")
    print("=" * 60)

    # 1. Buat email tempmail baru
    print("[*] Generating new TempMail address...")
    tm = TempMailClient()
    email = tm.create_address()
    print(f"[+] TempMail created: {email}")

    # 2. Start bridge
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
    opts.add_argument("--window-size=1366,768")
    opts.add_argument(f"--proxy-server=http://127.0.0.1:{DEFAULT_PORT}")
    opts.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(executable_path=CHROMEDRIVER_BIN) if os.path.exists(CHROMEDRIVER_BIN) else None
    driver = webdriver.Chrome(service=service, options=opts) if service else webdriver.Chrome(options=opts)

    session_data = {
        "email": email,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "steps": []
    }

    try:
        print("[*] Navigating to https://muse.ai ...")
        driver.get("https://muse.ai")
        time.sleep(3)

        wait = WebDriverWait(driver, 15)

        # Cari input email
        print("[*] Locating email input...")
        email_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Mobile number or email'], input[inputmode='email']")))
        
        # Scroll & ketik email
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", email_inp)
        time.sleep(0.3)
        email_inp.clear()
        email_inp.send_keys(email)
        print(f"[+] Email typed: {email}")

        driver.save_screenshot(step1_png)

        # Cari tombol Continue (type='submit')
        print("[*] Submitting form (clicking Continue)...")
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", submit_btn)

        print("[*] Waiting for response / next step...")
        time.sleep(5)

        current_url = driver.current_url
        page_title = driver.title
        driver.save_screenshot(step2_png)
        print(f"[+] After submit URL  : {current_url}")
        print(f"[+] After submit Title: {page_title}")
        print(f"[+] Screenshot saved  : {step2_png}")

        # Analisis elemen baru di halaman
        body_text = driver.find_element(By.TAG_NAME, "body").text
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print("\n[*] Visible inputs on current step:")
        for idx, inp in enumerate(inputs):
            name = inp.get_attribute("name") or "(no name)"
            t = inp.get_attribute("type") or "text"
            ph = inp.get_attribute("placeholder") or ""
            val = inp.get_attribute("value") or ""
            print(f"    [{idx+1}] type='{t}' name='{name}' placeholder='{ph}' val='{val}'")

        print("\n[*] Page text snippet (first 300 chars):")
        print("    " + repr(body_text[:300]))

        # Cek jika ada OTP / Password / Kode verifikasi
        is_otp = any(k in body_text.lower() for k in ["code", "verification", "check your email", "sent a code", "digit"])
        session_data["is_otp"] = is_otp
        session_data["after_url"] = current_url
        session_data["body_snippet"] = body_text[:500]

        if is_otp:
            print("\n[!] OTP / Verification code step detected! Polling TempMail inbox...")
            otp = tm.wait_for_otp(email, timeout=60, poll_interval=3)
            if otp:
                print(f"[✅] OTP Received: {otp}")
                session_data["otp"] = otp
            else:
                print("[-] OTP not received within timeout.")

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2)

        return session_data

    except Exception as e:
        print(f"[-] Signup automation exception: {e}", file=sys.stderr)
        driver.save_screenshot(os.path.join(base_dir, "error.png"))
        return {"status": "error", "message": str(e)}
    finally:
        driver.quit()
        bridge.stop()


if __name__ == "__main__":
    run_signup()
