#!/usr/bin/env python3
"""
Full Autonomous Muse.ai Signup Engine
Powered by TempMail CF (mail.berkahkita49.biz.id) & RainProxy US Residential
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
from tempmail_api import BerkahTempMail
from bridge import ProxyBridge, DEFAULT_PORT

CHROMIUM_BIN = os.environ.get("CHROMIUM_PATH") or "/data/data/com.termux/files/usr/bin/chromium-browser"
CHROMEDRIVER_BIN = os.environ.get("CHROMEDRIVER_PATH") or "/data/data/com.termux/files/usr/bin/chromedriver"


def run_signup_flow():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    res_file = os.path.join(base_dir, "account_created.json")

    print("=" * 65)
    print("      MUSE.AI AUTONOMOUS SIGNUP AGENT (TERMUX RESIDENTIAL)      ")
    print("=" * 65)

    # 1. Inisialisasi TempMail
    tm = BerkahTempMail()
    inbox = tm.create_inbox()
    email = inbox["address"]
    session_token = inbox["session"]
    print(f"[+] TempMail Created : {email}")

    # 2. Inisialisasi RainProxy Bridge
    bridge = ProxyBridge(local_port=DEFAULT_PORT)
    bridge.start(daemon=True)
    time.sleep(0.5)

    # 3. Boot Headless Chromium
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
    wait = WebDriverWait(driver, 20)

    account_info = {
        "email": email,
        "session_token": session_token,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "steps": []
    }

    try:
        # Step 1: Buka Landing Page
        print("\n[Step 1] Membuka https://muse.ai via RainProxy US...")
        driver.get("https://muse.ai")
        time.sleep(3)

        # Input Email
        email_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Mobile number or email'], input[inputmode='email']")))
        email_inp.clear()
        email_inp.send_keys(email)
        print(f"[+] Mengisi email: {email}")

        driver.save_screenshot(os.path.join(base_dir, "step1_email_entered.png"))

        # Klik Continue
        continue_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", continue_btn)
        print("[+] Tombol Continue diklik. Menunggu layar OTP...")

        # Step 2: Deteksi Layar OTP
        otp_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[maxlength='6']")))
        print("[+] Layar verifikasi OTP aktif terdeteksi.")
        driver.save_screenshot(os.path.join(base_dir, "step2_otp_screen.png"))

        # Step 3: Polling Kode OTP dari TempMail
        print("[Step 2] Polling kode verifikasi dari TempMail...")
        code, msg_detail = tm.wait_for_code(email, session=session_token, timeout=60, poll_interval=2)
        if not code:
            raise RuntimeError("Gagal mendapatkan kode verifikasi OTP dari Meta.")

        account_info["otp_code"] = code
        print(f"[+] Memasukkan kode OTP: {code}")

        # Ketik OTP
        otp_inp.send_keys(code)
        time.sleep(1)

        driver.save_screenshot(os.path.join(base_dir, "step3_otp_typed.png"))

        # Step 4: Klik Confirm jika ada tombol Confirm
        confirm_buttons = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
        if confirm_buttons:
            for cb in confirm_buttons:
                if "confirm" in cb.text.lower() or cb.get_attribute("type") == "submit":
                    try:
                        driver.execute_script("arguments[0].click();", cb)
                        print("[+] Tombol Confirm diklik.")
                        break
                    except Exception:
                        pass

        # Tunggu respon setelah confirm
        print("[Step 3] Menunggu respon verifikasi...")
        time.sleep(6)

        driver.save_screenshot(os.path.join(base_dir, "step4_after_confirm.png"))
        after_url = driver.current_url
        after_title = driver.title
        body_text = driver.find_element(By.TAG_NAME, "body").text

        print(f"[+] Post-Confirm URL   : {after_url}")
        print(f"[+] Post-Confirm Title : {after_title}")
        print(f"[*] Page Content Preview:\n{repr(body_text[:400])}")

        # Cek apakah ada langkah lanjutan (misal: password, profil, onboarding, atau captcha)
        inputs_after = driver.find_elements(By.TAG_NAME, "input")
        print("\n[*] Input fields pada langkah saat ini:")
        for idx, inp in enumerate(inputs_after):
            t = inp.get_attribute("type") or "text"
            n = inp.get_attribute("name") or ""
            ph = inp.get_attribute("placeholder") or ""
            print(f"    [{idx+1}] type='{t}' name='{n}' placeholder='{ph}'")

        # Ambil cookies sesi
        cookies = driver.get_cookies()
        account_info["final_url"] = after_url
        account_info["final_title"] = after_title
        account_info["cookies"] = cookies
        account_info["status"] = "verified"

        with open(res_file, "w", encoding="utf-8") as f:
            json.dump(account_info, f, indent=2)
        print(f"\n[✅] Sesi akun tersimpan di: {res_file}")

        return account_info

    except Exception as e:
        print(f"[-] Terjadi kesalahan: {e}", file=sys.stderr)
        driver.save_screenshot(os.path.join(base_dir, "error_signup.png"))
        return {"status": "error", "error": str(e)}
    finally:
        driver.quit()
        bridge.stop()


if __name__ == "__main__":
    run_signup_flow()
