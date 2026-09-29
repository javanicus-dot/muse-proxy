#!/usr/bin/env python3
"""
Autonomous Facebook Registration via TempMail CF & RainProxy US
"""

import sys
import os
import time
import json
import random
import re
from datetime import datetime

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


def select_fb_combo(driver, combo_element, value_text):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", combo_element)
    time.sleep(0.3)
    driver.execute_script("arguments[0].click();", combo_element)
    time.sleep(0.6)
    
    options = driver.find_elements(By.CSS_SELECTOR, "[role='option']")
    for opt in options:
        if opt.text.strip().lower() == str(value_text).strip().lower():
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", opt)
            time.sleep(0.4)
            return True
    return False


def register_fb_account(first_name="Alex", last_name="Santoso", birth_month="May", birth_day="15", birth_year="1998", gender="Male"):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fb_acc_out = os.path.join(base_dir, "fb_registered_account.json")

    print("=" * 65)
    print("      FACEBOOK AUTONOMOUS REGISTRATION (RAINPROXY US)      ")
    print(f"  Name     : {first_name} {last_name}")
    print(f"  Birthday : {birth_day} {birth_month} {birth_year}")
    print(f"  Gender   : {gender}")
    print("=" * 65)

    # 1. Inisialisasi TempMail
    tm = BerkahTempMail()
    inbox = tm.create_inbox()
    email = inbox["address"]
    session_token = inbox["session"]
    password = f"WuzzMeta@{random.randint(1000, 9999)}!"
    print(f"[+] TempMail Email    : {email}")
    print(f"[+] Generated Password: {password}")

    # 2. Start Proxy Bridge
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
    opts.add_argument("--window-size=1366,1080")
    opts.add_argument(f"--proxy-server=http://127.0.0.1:{DEFAULT_PORT}")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(executable_path=CHROMEDRIVER_BIN) if os.path.exists(CHROMEDRIVER_BIN) else None
    driver = webdriver.Chrome(service=service, options=opts) if service else webdriver.Chrome(options=opts)
    wait = WebDriverWait(driver, 25)

    account_record = {
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
        "birthday": f"{birth_day} {birth_month} {birth_year}",
        "gender": gender,
        "session_token": session_token,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        print("\n[Step 1] Membuka https://www.facebook.com/r.php ...")
        driver.get("https://www.facebook.com/r.php")
        time.sleep(3)

        # Cari dropdowns
        combos = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[role='combobox']")))
        print(f"[+] Ditemukan {len(combos)} combobox.")

        print(f"[*] Memilih Month: {birth_month}...")
        select_fb_combo(driver, combos[0], birth_month)
        print(f"[*] Memilih Day: {birth_day}...")
        select_fb_combo(driver, combos[1], birth_day)
        print(f"[*] Memilih Year: {birth_year}...")
        select_fb_combo(driver, combos[2], birth_year)
        print(f"[*] Memilih Gender: {gender}...")
        select_fb_combo(driver, combos[3], gender)

        # Cari text inputs
        inputs = driver.find_elements(By.TAG_NAME, "input")
        text_inputs = [i for i in inputs if i.get_attribute("type") in ["text", "password"] and i.is_displayed()]
        print(f"[+] Ditemukan {len(text_inputs)} field input teks.")

        if len(text_inputs) >= 4:
            print(f"[*] Mengisi Nama Depan: {first_name}...")
            type_slowly(text_inputs[0], first_name)
            print(f"[*] Mengisi Nama Belakang: {last_name}...")
            type_slowly(text_inputs[1], last_name)
            print(f"[*] Mengisi Email: {email}...")
            type_slowly(text_inputs[2], email)
            print(f"[*] Mengisi Password: {password}...")
            type_slowly(text_inputs[3], password)

        time.sleep(1)
        driver.save_screenshot(os.path.join(base_dir, "fb_form_filled.png"))
        print("[+] Screenshot form terisi disimpan: fb_form_filled.png")

        # Klik tombol Submit
        print("\n[Step 2] Menyerahkan formulir pendaftaran...")
        submit_btn = None
        for b in driver.find_elements(By.CSS_SELECTOR, "[role='button'], button"):
            if b.text.strip().lower() == "submit" or "submit" in b.text.lower():
                submit_btn = b
                break

        if not submit_btn:
            raise RuntimeError("Tombol Submit pendaftaran Facebook tidak ditemukan.")

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", submit_btn)
        print("[+] Tombol Submit diklik. Menunggu respons server Facebook...")
        time.sleep(8)

        driver.save_screenshot(os.path.join(base_dir, "fb_after_submit.png"))
        current_url = driver.current_url
        current_title = driver.title
        body_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"[+] Post-Submit URL   : {current_url}")
        print(f"[+] Post-Submit Title : {current_title}")
        print(f"[*] Body text preview : {repr(body_text[:300])}")

        # Cek apakah meminta konfirmasi kode OTP email
        if any(w in body_text.lower() for w in ["code", "confirm", "sent a code", "check your email", "kode"]):
            print("\n[Step 3] Facebook meminta verifikasi kode email. Menunggu pesan masuk di TempMail...")
            code = None
            start_poll = time.time()
            while time.time() - start_poll < 60:
                msgs = tm.get_messages(email, session=session_token)
                for m in msgs:
                    subj = m.get("subject", "")
                    cd = m.get("code")
                    if cd:
                        code = cd
                        break
                    match = re.search(r'\bFB-(\d{5,6})\b', subj) or re.search(r'\b(\d{5,6})\b', subj)
                    if match:
                        code = match.group(1)
                        break
                if code:
                    break
                time.sleep(2)

            if code:
                print(f"[✅] KODE FACEBOOK DITERIMA: {code}")
                account_record["fb_code"] = code
                # Cari input kode di layar FB
                code_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[inputmode='numeric']")
                if code_inputs:
                    code_inp = [ci for ci in code_inputs if ci.is_displayed()][0]
                    type_slowly(code_inp, code)
                    print(f"[+] Kode {code} diisikan ke input konfirmasi.")
                    time.sleep(0.5)

                    # Cari tombol konfirmasi
                    c_btns = driver.find_elements(By.CSS_SELECTOR, "[role='button'], button")
                    for cb in c_btns:
                        if cb.is_displayed() and any(w in cb.text.lower() for w in ["continue", "confirm", "next", "lanjutkan"]):
                            driver.execute_script("arguments[0].click();", cb)
                            print(f"[+] Tombol '{cb.text.strip()}' diklik.")
                            time.sleep(6)
                            break
            else:
                print("[-] Kode Facebook belum masuk atau terkirim via link.")

        driver.save_screenshot(os.path.join(base_dir, "fb_final_state.png"))
        account_record["final_url"] = driver.current_url
        account_record["final_title"] = driver.title
        account_record["cookies"] = driver.get_cookies()

        with open(fb_acc_out, "w", encoding="utf-8") as f:
            json.dump(account_record, f, indent=2)

        print(f"\n[🎉] Akun Facebook berhasil diproses! Tersimpan di: {fb_acc_out}")
        return account_record

    except Exception as e:
        print(f"[-] Facebook registration error: {e}", file=sys.stderr)
        driver.save_screenshot(os.path.join(base_dir, "fb_error.png"))
        return {"status": "error", "error": str(e)}
    finally:
        driver.quit()
        bridge.stop()


if __name__ == "__main__":
    register_fb_account()
