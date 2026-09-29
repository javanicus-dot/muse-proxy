#!/usr/bin/env python3
"""
Full Autonomous Facebook Checkpoint Solver & Muse.ai OAuth Linker
1. Logs into Facebook (Betsy / Alex Santoso)
2. Captures CAPTCHA challenge
3. Solves CAPTCHA via 2Captcha ImageToTextTask
4. Submits solution & verifies Facebook profile unlock
5. Navigates to Muse.ai /access/verification
6. Clicks 'Link Facebook account' & approves Meta Accounts Center linking
"""

import sys
import os
import time
import json
import base64
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bridge import ProxyBridge, DEFAULT_PORT

API_KEY_2CAPTCHA = "4bb9e2d66b71bb7a63b0c3738619df8e"
CHROMIUM_BIN = os.environ.get("CHROMIUM_PATH") or "/data/data/com.termux/files/usr/bin/chromium-browser"
CHROMEDRIVER_BIN = os.environ.get("CHROMEDRIVER_PATH") or "/data/data/com.termux/files/usr/bin/chromedriver"


def type_slowly(element, text, delay=0.04):
    for ch in text:
        element.send_keys(ch)
        time.sleep(delay)


def solve_captcha_2captcha(image_path):
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    res = requests.post("https://api.2captcha.com/createTask", json={
        "clientKey": API_KEY_2CAPTCHA,
        "task": {
            "type": "ImageToTextTask",
            "body": b64
        }
    }).json()

    task_id = res.get("taskId")
    if not task_id:
        print(f"[-] 2Captcha error: {res}")
        return None

    print(f"[*] 2Captcha Task ID: {task_id}, polling for solution...")
    for _ in range(20):
        time.sleep(2)
        poll = requests.post("https://api.2captcha.com/getTaskResult", json={
            "clientKey": API_KEY_2CAPTCHA,
            "taskId": task_id
        }).json()
        if poll.get("status") == "ready":
            sol = poll.get("solution", {}).get("text")
            print(f"[✅] 2Captcha Solved: {sol}")
            return sol
    return None


def run_solve_and_link():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fb_email = "betsy767@berkahkita49.biz.id"
    fb_pass = "WuzzMeta@9340!"

    print("=" * 65)
    print("   AUTONOMOUS FB CHECKPOINT SOLVER & MUSE.AI OAUTH LINKER   ")
    print(f"  Facebook Account : {fb_email}")
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
        # Step 1: Login Facebook
        print("\n[Step 1] Membuka https://www.facebook.com/login/ ...")
        driver.get("https://www.facebook.com/login/")
        time.sleep(3)

        email_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email'], input#email")))
        type_slowly(email_inp, fb_email)
        pass_inp = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='pass'], input#pass")))
        type_slowly(pass_inp, fb_pass)
        pass_inp.send_keys(Keys.ENTER)
        time.sleep(6)

        print(f"[+] Post-Login URL   : {driver.current_url}")
        print(f"[+] Post-Login Title : {driver.title}")

        # Checkpoint handling
        if "checkpoint" in driver.current_url:
            print("\n[Step 2] Checkpoint terdeteksi. Mencari CAPTCHA challenge...")
            time.sleep(3)

            # Jika ada tombol Continue awal
            cont_btn = driver.find_elements(By.XPATH, "//div[@role='button'][contains(., 'Continue')] | //button[contains(., 'Continue')]")
            if cont_btn and any(b.is_displayed() for b in cont_btn):
                for b in cont_btn:
                    if b.is_displayed():
                        driver.execute_script("arguments[0].click();", b)
                        print("[+] Tombol Continue awal diklik.")
                        time.sleep(5)
                        break

            # Cari elemen gambar CAPTCHA
            captcha_img = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "img[alt*='Captcha challenge']")))
            captcha_path = os.path.join(base_dir, "live_fb_captcha.png")
            time.sleep(1)
            captcha_img.screenshot(captcha_path)
            print(f"[+] Gambar CAPTCHA ditangkap: {captcha_path}")

            # Solve via 2Captcha
            solution = solve_captcha_2captcha(captcha_path)
            if not solution:
                raise RuntimeError("Gagal memecahkan CAPTCHA Facebook via 2Captcha.")

            # Isi jawaban CAPTCHA
            inp = driver.find_element(By.CSS_SELECTOR, "input[type='text']:not([type='hidden'])")
            inp.clear()
            type_slowly(inp, solution)
            print(f"[+] Jawaban CAPTCHA '{solution}' diisikan ke input field.")
            time.sleep(1)

            # Klik tombol Continue untuk submit CAPTCHA
            submit_c = driver.find_element(By.XPATH, "//div[@role='button'][contains(., 'Continue')] | //button[contains(., 'Continue')]")
            driver.execute_script("arguments[0].click();", submit_c)
            print("[+] CAPTCHA disubmit. Menunggu verifikasi...")
            time.sleep(8)

            driver.save_screenshot(os.path.join(base_dir, "after_captcha_submit.png"))
            print(f"[+] After CAPTCHA URL: {driver.current_url}")
            print(f"[+] After CAPTCHA Title: {driver.title}")

        # Step 3: Inject Sesi Akun Muse.ai
        print("\n[Step 3] Menginjeksikan sesi akun Muse.ai...")
        driver.get("https://muse.ai")
        time.sleep(2)

        with open(os.path.join(base_dir, "registered_account.json")) as f:
            muse_acc = json.load(f)

        for c in muse_acc.get("cookies", []):
            try:
                driver.add_cookie({"name": c["name"], "value": c["value"]})
            except Exception:
                pass

        # Step 4: Buka Halaman Verifikasi Umur Muse
        print("\n[Step 4] Membuka https://muse.ai/access/verification ...")
        driver.get("https://muse.ai/access/verification")
        time.sleep(5)

        driver.save_screenshot(os.path.join(base_dir, "muse_verif_before_link.png"))
        print(f"[+] Muse URL   : {driver.current_url}")
        print(f"[+] Muse Title : {driver.title}")

        parent_handle = driver.current_window_handle

        # Klik 'Link Facebook account'
        fb_btn = None
        for b in driver.find_elements(By.TAG_NAME, "button"):
            if "facebook" in b.text.lower():
                fb_btn = b
                break

        if fb_btn:
            print("[+] Mengklik 'Link Facebook account'...")
            driver.execute_script("arguments[0].click();", fb_btn)
            time.sleep(6)

            # Cek jika ada popup OAuth
            handles = driver.window_handles
            if len(handles) > 1:
                popup = [h for h in handles if h != parent_handle][0]
                driver.switch_to.window(popup)
                print(f"[+] Berpindah ke popup: {driver.current_url}")
                driver.save_screenshot(os.path.join(base_dir, "popup_oauth_step.png"))

                # Cek tombol konfirmasi (Continue as Alex / Link account)
                for b in driver.find_elements(By.TAG_NAME, "button"):
                    txt = b.text.lower()
                    if any(w in txt for w in ["continue as", "confirm", "allow", "yes, continue", "lanjutkan"]):
                        print(f"[+] Otorisasi Akun Facebook: '{b.text.strip()}'...")
                        driver.execute_script("arguments[0].click();", b)
                        time.sleep(6)
                        break

                time.sleep(4)
                if popup in driver.window_handles:
                    driver.close()

                driver.switch_to.window(parent_handle)

            time.sleep(6)
            driver.save_screenshot(os.path.join(base_dir, "muse_final_state_after_link.png"))
            print(f"\n[🎉] Final Muse URL   : {driver.current_url}")
            print(f"[🎉] Final Muse Title : {driver.title}")
            body_preview = driver.find_element(By.TAG_NAME, "body").text
            print(f"[*] Konten Layar Muse:\n{repr(body_preview[:400])}")

        else:
            print("[-] Tombol Link Facebook tidak ditemukan.")

    except Exception as e:
        print(f"[-] Kesalahan pipeline: {e}", file=sys.stderr)
        driver.save_screenshot(os.path.join(base_dir, "pipeline_error.png"))
    finally:
        driver.quit()
        bridge.stop()


if __name__ == "__main__":
    run_solve_and_link()
