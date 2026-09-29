#!/usr/bin/env python3
"""
Muse.ai OAuth Account Linker (Instagram / Facebook)
Bypasses Age Verification Gate via Meta Accounts Center Linking
"""

import sys
import os
import time
import json
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    import pyotp
except ImportError:
    pyotp = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bridge import ProxyBridge, DEFAULT_PORT

CHROMIUM_BIN = os.environ.get("CHROMIUM_PATH") or "/data/data/com.termux/files/usr/bin/chromium-browser"
CHROMEDRIVER_BIN = os.environ.get("CHROMEDRIVER_PATH") or "/data/data/com.termux/files/usr/bin/chromedriver"


def type_slowly(element, text, delay=0.03):
    for ch in text:
        element.send_keys(ch)
        time.sleep(delay)


def parse_credentials(raw_str):
    parts = raw_str.strip().split("|")
    user = parts[0].strip()
    pwd = parts[1].strip() if len(parts) > 1 else ""
    totp = parts[2].strip() if len(parts) > 2 else ""
    return user, pwd, totp


def link_oauth(provider="instagram", credentials_raw=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    account_file = os.path.join(base_dir, "registered_account.json")

    if not os.path.exists(account_file):
        print(f"[-] File akun {account_file} tidak ditemukan. Jalankan signup terlebih dahulu.", file=sys.stderr)
        return False

    with open(account_file, "r", encoding="utf-8") as f:
        account_data = json.load(f)

    user = pwd = totp = ""
    if credentials_raw:
        user, pwd, totp = parse_credentials(credentials_raw)

    print("=" * 65)
    print("      MUSE.AI OAUTH AGE VERIFICATION LINKER      ")
    print(f"  Target Provider : {provider.upper()}")
    print(f"  Account User    : {user if user else '(Manual input / check URL)'}")
    print("=" * 65)

    # 1. Start Proxy Bridge
    bridge = ProxyBridge(local_port=DEFAULT_PORT)
    bridge.start(daemon=True)
    time.sleep(0.5)

    # 2. Boot Chromium
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
    driver = webdriver.Chrome(service=service, options=opts) if service else webdriver.Chrome(options=opts)
    wait = WebDriverWait(driver, 25)

    try:
        # Load muse.ai dan injeksi cookies yang sudah verified
        print("[*] Menginjeksikan sesi akun muse.ai...")
        driver.get("https://muse.ai")
        time.sleep(2)

        for cookie in account_data.get("cookies", []):
            try:
                driver.add_cookie(cookie)
            except Exception:
                pass

        # Navigasi ke halaman verifikasi umur
        print("[*] Membuka halaman verifikasi umur https://muse.ai/access/verification ...")
        driver.get("https://muse.ai/access/verification")
        time.sleep(4)

        parent_handle = driver.current_window_handle

        # Cari tombol link Instagram atau Facebook
        target_btn = None
        for b in driver.find_elements(By.TAG_NAME, "button"):
            txt = b.text.lower()
            if provider == "instagram" and "instagram" in txt:
                target_btn = b
                break
            elif provider == "facebook" and "facebook" in txt:
                target_btn = b
                break

        if not target_btn:
            raise RuntimeError(f"Tombol Link {provider.capitalize()} tidak ditemukan di halaman.")

        print(f"[+] Mengklik tombol: '{target_btn.text.strip()}'...")
        driver.execute_script("arguments[0].click();", target_btn)
        time.sleep(5)

        # Cek apakah terbuka window/tab popup baru
        handles = driver.window_handles
        popup_handle = None
        for h in handles:
            if h != parent_handle:
                popup_handle = h
                break

        if popup_handle:
            print("[+] Popup OAuth terdeteksi. Beralih ke window popup...")
            driver.switch_to.window(popup_handle)
        else:
            print("[*] OAuth berjalan di tab yang sama.")

        time.sleep(3)
        oauth_url = driver.current_url
        oauth_title = driver.title
        print(f"[+] OAuth URL   : {oauth_url}")
        print(f"[+] OAuth Title : {oauth_title}")
        driver.save_screenshot(os.path.join(base_dir, f"oauth_{provider}_opened.png"))

        # Jika kredensial diberikan, lakukan auto-fill dan login
        if user and pwd:
            print(f"\n[*] Mengisi kredensial {provider.capitalize()} ({user})...")
            if provider == "instagram":
                u_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username'], input[placeholder*='username'], input[aria-label*='username']")))
                p_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='password'], input[type='password']")))
                u_inp.clear()
                type_slowly(u_inp, user)
                p_inp.clear()
                type_slowly(p_inp, pwd)
                time.sleep(0.5)

                login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                driver.execute_script("arguments[0].click();", login_btn)
                print("[+] Form login Instagram disubmit.")

            elif provider == "facebook":
                u_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email'], input#email")))
                p_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='pass'], input#pass, input[type='password']")))
                u_inp.clear()
                type_slowly(u_inp, user)
                p_inp.clear()
                type_slowly(p_inp, pwd)
                time.sleep(0.5)

                login_btn = driver.find_element(By.CSS_SELECTOR, "button[name='login'], button[type='submit']")
                driver.execute_script("arguments[0].click();", login_btn)
                print("[+] Form login Facebook disubmit.")

            time.sleep(6)
            driver.save_screenshot(os.path.join(base_dir, f"oauth_{provider}_after_submit.png"))

            # Cek jika ada 2FA
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            if any(k in page_text for k in ["two-factor", "security code", "enter code", "authentication code"]):
                print("[!] Layar 2FA terdeteksi!")
                if totp:
                    code_2fa = totp
                    if len(totp) > 8 and pyotp:
                        try:
                            totp_gen = pyotp.TOTP(totp)
                            code_2fa = totp_gen.now()
                            print(f"[+] Menghasilkan kode TOTP: {code_2fa}")
                        except Exception:
                            pass
                    code_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], input[inputmode='numeric']")))
                    type_slowly(code_inp, code_2fa)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", code_inp)
                    time.sleep(0.5)
                    submit_2fa = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                    driver.execute_script("arguments[0].click();", submit_2fa)
                    print("[+] Kode 2FA disubmit.")
                    time.sleep(6)

            # Cek jika ada consent / Accounts Center linking confirmation (Continue as ...)
            confirm_btns = driver.find_elements(By.TAG_NAME, "button")
            for cb in confirm_btns:
                t = cb.text.strip().lower()
                if any(w in t for w in ["continue as", "confirm", "allow", "yes, continue", "lanjutkan sebagai"]):
                    print(f"[+] Mengklik tombol otorisasi: '{cb.text.strip()}'...")
                    driver.execute_script("arguments[0].click();", cb)
                    time.sleep(5)
                    break

            # Tunggu popup menutup atau redirect kembali
            time.sleep(6)
            if popup_handle and popup_handle in driver.window_handles:
                driver.close()

            driver.switch_to.window(parent_handle)
            time.sleep(5)

            print("\n[*] Memeriksa status Muse AI setelah linking...")
            final_url = driver.current_url
            final_title = driver.title
            print(f"[+] Muse URL   : {final_url}")
            print(f"[+] Muse Title : {final_title}")
            driver.save_screenshot(os.path.join(base_dir, "dashboard_unlocked.png"))

            # Update cookies
            account_data["final_url"] = final_url
            account_data["final_title"] = final_title
            account_data["cookies"] = driver.get_cookies()
            account_data["oauth_linked"] = provider
            with open(account_file, "w", encoding="utf-8") as f:
                json.dump(account_data, f, indent=2)

            print(f"[✅] Sesi akun diperbarui di {account_file}")
            return True

        else:
            print("\n[ℹ️] Tidak ada kredensial yang diberikan. URL OAuth siap digunakan:")
            print(f"     URL: {oauth_url}")
            print("     Gunakan argumen --cred 'username|password' atau --cred 'email|password|2fa'")
            return True

    except Exception as e:
        print(f"[-] Kesalahan saat OAuth linking: {e}", file=sys.stderr)
        driver.save_screenshot(os.path.join(base_dir, f"oauth_{provider}_error.png"))
        return False
    finally:
        driver.quit()
        bridge.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Link Instagram or Facebook to bypass Muse.ai age verification")
    parser.add_argument("--provider", choices=["instagram", "facebook"], default="instagram", help="OAuth provider (default: instagram)")
    parser.add_argument("--cred", help="Credentials in raw pipe format: 'user|pass' or 'user|pass|totp_secret'")
    args = parser.parse_args()

    link_oauth(provider=args.provider, credentials_raw=args.cred)
