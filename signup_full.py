#!/usr/bin/env python3
"""
Complete Autonomous Muse.ai Registration Pipeline
TempMail CF (mail.berkahkita49.biz.id) + RainProxy US + Headless Chromium
"""

import sys
import os
import time
import json
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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


def run_full_signup(first_name="Wuzz", last_name="Store", birth_year="1998", birth_month="May", birth_day="15"):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    account_out = os.path.join(base_dir, "registered_account.json")

    print("=" * 65)
    print("      MUSE.AI FULL SIGNUP AGENT (TERMUX RESIDENTIAL)      ")
    print(f"  Name      : {first_name} {last_name}")
    print(f"  Birthday  : {birth_day} {birth_month} {birth_year}")
    print("=" * 65)

    # 1. Create TempMail
    tm = BerkahTempMail()
    inbox = tm.create_inbox()
    email = inbox["address"]
    session_token = inbox["session"]
    print(f"[+] TempMail Generated : {email}")

    # 2. Start Proxy Bridge
    bridge = ProxyBridge(local_port=DEFAULT_PORT)
    bridge.start(daemon=True)
    time.sleep(0.5)

    # 3. Launch Headless Chromium
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
    wait = WebDriverWait(driver, 25)

    account_data = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "birth_date": f"{birth_day} {birth_month} {birth_year}",
        "session_token": session_token,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        # Step 1: Landing Page
        print("\n[Step 1] Navigating to https://muse.ai ...")
        driver.get("https://muse.ai")
        time.sleep(3)

        email_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Mobile number or email'], input[inputmode='email']")))
        email_inp.clear()
        time.sleep(0.3)
        type_slowly(email_inp, email)
        print(f"[+] Typed email: {email}")
        time.sleep(0.5)

        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        print(f"[+] Submit button enabled: {submit_btn.is_enabled()}")
        driver.execute_script("arguments[0].click();", submit_btn)
        print("[+] Clicked Continue.")

        # Step 2: OTP Verification
        print("\n[Step 2] Awaiting OTP Screen & Polling TempMail...")
        otp_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[maxlength='6']")))
        driver.save_screenshot(os.path.join(base_dir, "step2_otp_screen.png"))
        
        code, msg = tm.wait_for_code(email, session=session_token, timeout=60, poll_interval=2)
        if not code:
            raise RuntimeError("OTP verification code not received from Meta.")
        
        account_data["otp"] = code
        print(f"[+] Entering OTP Code: {code}")
        type_slowly(otp_inp, code, delay=0.05)
        time.sleep(1)

        # Klik Confirm jika ada tombol submit aktif
        submit_btns = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
        for b in submit_btns:
            if b.is_enabled() and ("confirm" in b.text.lower() or b.get_attribute("type") == "submit"):
                driver.execute_script("arguments[0].click();", b)
                print("[+] Clicked Confirm on OTP screen.")
                break

        print("[*] Waiting for screen transition after OTP...")
        time.sleep(5)
        driver.save_screenshot(os.path.join(base_dir, "step3_after_otp.png"))

        # Step 3: Handle Birthday Setup
        print("\n[Step 3] Configuring Birthday...")
        try:
            year_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Year']")))
            driver.execute_script("arguments[0].click();", year_btn)
            time.sleep(0.6)

            year_options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
            opt_year = [o for o in year_options if o.text.strip() == str(birth_year)]
            if opt_year:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", opt_year[0])
                print(f"[+] Selected Year: {birth_year}")
            time.sleep(0.5)

            month_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Month']")
            driver.execute_script("arguments[0].click();", month_btn)
            time.sleep(0.6)
            month_options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
            opt_month = [o for o in month_options if o.text.strip() == str(birth_month)]
            if opt_month:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", opt_month[0])
                print(f"[+] Selected Month: {birth_month}")
            time.sleep(0.5)

            day_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Day']")
            driver.execute_script("arguments[0].click();", day_btn)
            time.sleep(0.6)
            day_options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
            opt_day = [o for o in day_options if o.text.strip() == str(birth_day)]
            if opt_day:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", opt_day[0])
                print(f"[+] Selected Day: {birth_day}")
            time.sleep(0.5)
        except Exception as e:
            print(f"[-] Birthday dropdown notice: {e}")

        # Step 4: Handle Name Fields
        print("\n[Step 4] Checking for Name Fields...")
        time.sleep(1)
        
        # Cari SEMUA tag input di halaman (apapun type-nya)
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        visible_inputs = [i for i in all_inputs if i.is_displayed() and "sr-only" not in (i.get_attribute("class") or "")]
        print(f"[*] Total input elements found: {len(all_inputs)} (visible: {len(visible_inputs)})")
        
        first_input = None
        last_input = None

        for inp in visible_inputs:
            ph = (inp.get_attribute("placeholder") or "").lower()
            aria = (inp.get_attribute("aria-label") or "").lower()
            name = (inp.get_attribute("name") or "").lower()
            val = (inp.get_attribute("value") or "")
            print(f"    - Input ph='{ph}' aria='{aria}' name='{name}' val='{val}'")
            if "first" in ph or "first" in aria or "first" in name:
                first_input = inp
            elif "last" in ph or "last" in aria or "last" in name:
                last_input = inp

        if not first_input and len(visible_inputs) >= 2:
            first_input = visible_inputs[0]
            last_input = visible_inputs[1]

        if first_input:
            first_input.clear()
            type_slowly(first_input, first_name)
            driver.execute_script("""
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, first_input)
            print(f"[+] Filled First Name: {first_name}")

        if last_input:
            last_input.clear()
            type_slowly(last_input, last_name)
            driver.execute_script("""
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, last_input)
            print(f"[+] Filled Last Name: {last_name}")

        time.sleep(1)
        driver.save_screenshot(os.path.join(base_dir, "step4_form_filled.png"))

        # Step 5: Submit Final Registration
        print("\n[Step 5] Submitting Final Confirmation...")
        confirm_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button[type='submit'], button[data-pel-click*='continue'], button[data-pel-click*='confirm']")))
        print(f"[+] Found Confirm button: text='{confirm_btn.text.strip()}', enabled={confirm_btn.is_enabled()}")

        # Klik submit
        driver.execute_script("arguments[0].click();", confirm_btn)

        # Wait for account creation process
        print("[*] Processing account creation on Meta backend...")
        time.sleep(10)

        # Cek jika ada redirect atau next screen
        final_url = driver.current_url
        final_title = driver.title
        body_text = driver.find_element(By.TAG_NAME, "body").text
        screenshot_final = os.path.join(base_dir, "step5_final_state.png")
        driver.save_screenshot(screenshot_final)

        print(f"\n[+] Final URL    : {final_url}")
        print(f"[+] Final Title  : {final_title}")
        print(f"[+] Screenshot   : {screenshot_final}")
        print(f"[*] Page Content Preview (first 400 chars):\n{repr(body_text[:400])}")

        # Simpan cookies sesi lengkap
        cookies = driver.get_cookies()
        account_data["status"] = "success"
        account_data["final_url"] = final_url
        account_data["final_title"] = final_title
        account_data["cookies"] = cookies
        account_data["body_snippet"] = body_text[:600]

        with open(account_out, "w", encoding="utf-8") as f:
            json.dump(account_data, f, indent=2)

        print(f"\n[🎉] Pendaftaran Berhasil! Detail akun tersimpan di: {account_out}")
        return account_data

    except Exception as e:
        print(f"[-] Signup pipeline failure: {e}", file=sys.stderr)
        traceback.print_exc()
        driver.save_screenshot(os.path.join(base_dir, "signup_failure.png"))
        return {"status": "error", "error": str(e)}
    finally:
        driver.quit()
        bridge.stop()


if __name__ == "__main__":
    run_full_signup()
