#!/usr/bin/env python3
"""
Full Autonomous Meta Account Auth & CCV Age Verification Chain
1. Authenticates on auth.meta.com using TempMail (mariela674@berkahkita49.biz.id)
2. Injects / navigates to muse.ai /access/verification
3. Clicks 'Confirm age'
4. Completes CCV Age Verification checkout on auth.meta.com/payments/checkout/
5. Unlocks Muse.ai dashboard
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


def type_slowly(element, text, delay=0.03):
    for ch in text:
        element.send_keys(ch)
        time.sleep(delay)


def run_chain():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    email = "mariela674@berkahkita49.biz.id"
    tm = BerkahTempMail()

    print("=" * 65)
    print("      MUSE.AI AGE VERIFICATION & CCV CHECKOUT AGENT      ")
    print(f"  Target Account : {email}")
    print("=" * 65)

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
        # Step 1: Login auth.meta.com
        print("\n[Step 1] Membuka https://auth.meta.com/ ...")
        driver.get("https://auth.meta.com/")
        time.sleep(3)

        btn = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Use mobile number')] | //div[@role='button'][contains(., 'email')]")))
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(3)

        email_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], input[type='email']")))
        email_inp.clear()
        type_slowly(email_inp, email)
        time.sleep(0.5)

        cont_btn = driver.find_element(By.XPATH, "//div[@role='button'][contains(., 'Continue')] | //button[contains(., 'Continue')]")
        driver.execute_script("arguments[0].click();", cont_btn)
        print(f"[+] Email {email} disubmit. Menunggu OTP masuk ke TempMail...")
        time.sleep(4)

        driver.save_screenshot(os.path.join(base_dir, "meta_otp_screen.png"))

        code, _ = tm.wait_for_code(email, timeout=60)
        if not code:
            raise RuntimeError("Kode verifikasi OTP Meta tidak diterima.")

        print(f"[+] Kode OTP Diterima: {code}")
        otp_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']:not([disabled]), input[inputmode='numeric']")))
        type_slowly(otp_inp, code, delay=0.04)
        time.sleep(1)

        submit_otp = driver.find_element(By.XPATH, "//div[@role='button'][contains(., 'Continue')] | //button[contains(., 'Continue')]")
        driver.execute_script("arguments[0].click();", submit_otp)
        print("[+] OTP disubmit. Menunggu login Meta berhasil...")
        time.sleep(8)

        print(f"[+] Post-Login URL   : {driver.current_url}")
        print(f"[+] Post-Login Title : {driver.title}")
        driver.save_screenshot(os.path.join(base_dir, "meta_logged_in.png"))

        # Step 2: Inject Sesi Muse.ai
        print("\n[Step 2] Membuka Muse.ai dan menginjeksikan cookies...")
        driver.get("https://muse.ai")
        time.sleep(2)

        with open(os.path.join(base_dir, "registered_account.json")) as f:
            muse_acc = json.load(f)

        for c in muse_acc.get("cookies", []):
            try:
                driver.add_cookie({"name": c["name"], "value": c["value"]})
            except Exception:
                pass

        # Step 3: Navigasi ke Verifikasi Umur Muse
        print("\n[Step 3] Membuka https://muse.ai/access/verification ...")
        driver.get("https://muse.ai/access/verification")
        time.sleep(5)

        driver.save_screenshot(os.path.join(base_dir, "muse_verif_ready.png"))
        print(f"[+] Muse Verif URL   : {driver.current_url}")
        print(f"[+] Muse Verif Title : {driver.title}")

        # Hook window.open
        driver.execute_script("""
            window.openedUrls = [];
            const originalOpen = window.open;
            window.open = function(url, ...args) {
                window.openedUrls.push(url);
                return originalOpen.apply(this, [url, ...args]);
            };
        """)

        # Klik Confirm age
        confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Confirm age')]")))
        print("[+] Mengklik tombol 'Confirm age'...")
        driver.execute_script("arguments[0].click();", confirm_btn)
        time.sleep(6)

        opened_urls = driver.execute_script("return window.openedUrls;")
        print(f"[+] URL Checkout dibuka: {opened_urls}")

        # Cek tab baru
        handles = driver.window_handles
        print(f"[+] Total tab browser: {len(handles)}")
        for idx, h in enumerate(handles):
            driver.switch_to.window(h)
            print(f"    Tab [{idx}] URL: {driver.current_url} | Title: {driver.title}")
            if "checkout" in driver.current_url or "payments" in driver.current_url:
                checkout_shot = os.path.join(base_dir, "checkout_screen.png")
                driver.save_screenshot(checkout_shot)
                print(f"[+] Screenshot checkout tersimpan: {checkout_shot}")
                body = driver.find_element(By.TAG_NAME, "body").text
                print(f"[*] Checkout body preview:\n{repr(body[:500])}")

                # Cek form kartu kredit
                inputs = driver.find_elements(By.TAG_NAME, "input")
                print(f"[*] Field input pada checkout: {len(inputs)}")
                for i_idx, inp in enumerate(inputs):
                    print(f"    - Input [{i_idx}] name={inp.get_attribute('name')}, type={inp.get_attribute('type')}, ph={inp.get_attribute('placeholder')}")

    except Exception as e:
        print(f"[-] Terjadi kesalahan: {e}", file=sys.stderr)
        driver.save_screenshot(os.path.join(base_dir, "chain_error.png"))
    finally:
        driver.quit()
        bridge.stop()


if __name__ == "__main__":
    run_chain()
