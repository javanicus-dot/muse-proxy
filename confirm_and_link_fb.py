#!/usr/bin/env python3
"""
Confirm Facebook Account & Link to Muse.ai
Email: betsy767@berkahkita49.biz.id
Password: WuzzMeta@9340!
Code: 73260
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


def run_confirm_and_link():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fb_email = "betsy767@berkahkita49.biz.id"
    fb_pass = "WuzzMeta@9340!"
    fb_code = "73260"

    print("=" * 65)
    print("      CONFIRM FACEBOOK & LINK TO MUSE.AI      ")
    print(f"  Facebook Email : {fb_email}")
    print(f"  Confirm Code   : {fb_code}")
    print("=" * 65)

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
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(executable_path=CHROMEDRIVER_BIN) if os.path.exists(CHROMEDRIVER_BIN) else None
    driver = webdriver.Chrome(service=service, options=opts)
    wait = WebDriverWait(driver, 25)

    try:
        # Step 1: Login Facebook
        print("\n[Step 1] Membuka https://www.facebook.com/login/ ...")
        driver.get("https://www.facebook.com/login/")
        time.sleep(3)

        email_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email'], input#email")))
        type_slowly(email_inp, fb_email)
        time.sleep(0.3)

        pass_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='pass'], input#pass")))
        type_slowly(pass_inp, fb_pass)
        time.sleep(0.5)

        print("[+] Mengirim ENTER pada form login Facebook...")
        pass_inp.send_keys(Keys.ENTER)
        
        # Fallback click
        try:
            time.sleep(1)
            btn = driver.find_element(By.XPATH, "//button[contains(., 'Log in')] | //div[@role='button'][contains(., 'Log in')]")
            driver.execute_script("arguments[0].click();", btn)
        except Exception:
            pass

        print("[+] Form login Facebook disubmit. Menunggu respons...")
        time.sleep(8)

        driver.save_screenshot(os.path.join(base_dir, "fb_login_result.png"))
        print(f"[+] FB URL: {driver.current_url}")
        print(f"[+] FB Title: {driver.title}")

        body_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"[*] FB Body Preview: {repr(body_text[:250])}")

        # Jika ada form konfirmasi kode
        if any(w in body_text.lower() for w in ["code", "confirm", "sent a code", "enter the code"]):
            print("[*] Layar konfirmasi kode Facebook terdeteksi...")
            code_inps = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[inputmode='numeric']")
            if code_inps:
                c_inp = [ci for ci in code_inps if ci.is_displayed()][0]
                type_slowly(c_inp, fb_code)
                print(f"[+] Mengisi kode verifikasi: {fb_code}")
                time.sleep(0.5)

                for b in driver.find_elements(By.CSS_SELECTOR, "button, [role='button']"):
                    if b.is_displayed() and any(w in b.text.lower() for w in ["continue", "confirm", "next"]):
                        driver.execute_script("arguments[0].click();", b)
                        print(f"[+] Mengklik tombol: '{b.text.strip()}'")
                        time.sleep(6)
                        break

        driver.save_screenshot(os.path.join(base_dir, "fb_after_confirm.png"))

        # Step 2: Inject Sesi Muse.ai
        print("\n[Step 2] Membuka Muse.ai dan menginjeksikan sesi akun...")
        driver.get("https://muse.ai")
        time.sleep(2)

        with open(os.path.join(base_dir, "registered_account.json")) as f:
            muse_acc = json.load(f)

        for c in muse_acc.get("cookies", []):
            try:
                driver.add_cookie({"name": c["name"], "value": c["value"]})
            except Exception:
                pass

        # Step 3: Buka Halaman Verifikasi Umur Muse
        print("\n[Step 3] Membuka https://muse.ai/access/verification ...")
        driver.get("https://muse.ai/access/verification")
        time.sleep(5)

        driver.save_screenshot(os.path.join(base_dir, "muse_verification_step.png"))
        print(f"[+] Muse URL   : {driver.current_url}")
        print(f"[+] Muse Title : {driver.title}")

        parent_handle = driver.current_window_handle

        # Cari tombol Link Facebook
        fb_link_btn = None
        for b in driver.find_elements(By.TAG_NAME, "button"):
            if "facebook" in b.text.lower():
                fb_link_btn = b
                break

        if fb_link_btn:
            print("[+] Tombol 'Link Facebook account' ditemukan! Mengklik...")
            driver.execute_script("arguments[0].click();", fb_link_btn)
            time.sleep(6)

            # Cek jika ada popup
            handles = driver.window_handles
            if len(handles) > 1:
                popup = [h for h in handles if h != parent_handle][0]
                driver.switch_to.window(popup)
                print(f"[+] Beralih ke popup OAuth: {driver.current_url}")
                driver.save_screenshot(os.path.join(base_dir, "popup_oauth_fb.png"))

                # Cari tombol otorisasi "Continue as Alex"
                for b in driver.find_elements(By.TAG_NAME, "button"):
                    txt = b.text.lower()
                    if any(w in txt for w in ["continue as", "confirm", "allow", "yes, continue", "lanjutkan"]):
                        print(f"[+] Menyetujui otorisasi: '{b.text.strip()}'...")
                        driver.execute_script("arguments[0].click();", b)
                        time.sleep(6)
                        break

                time.sleep(4)
                if popup in driver.window_handles:
                    driver.close()

                driver.switch_to.window(parent_handle)

            time.sleep(6)
            driver.save_screenshot(os.path.join(base_dir, "muse_final_unlocked.png"))
            print(f"\n[+] URL Terakhir Muse  : {driver.current_url}")
            print(f"[+] Title Terakhir Muse: {driver.title}")
            body_final = driver.find_element(By.TAG_NAME, "body").text
            print(f"[*] Preview Halaman:\n{repr(body_final[:400])}")

        else:
            print("[-] Tombol Link Facebook tidak ditemukan (mungkin URL sudah ter-unlock).")

    except Exception as e:
        print(f"[-] Terjadi kesalahan: {e}", file=sys.stderr)
        driver.save_screenshot(os.path.join(base_dir, "link_error.png"))
    finally:
        driver.quit()
        bridge.stop()


if __name__ == "__main__":
    run_confirm_and_link()
