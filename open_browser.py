#!/usr/bin/env python3
"""
Muse.ai Headless Chromium Browser Runner via RainProxy US
Opens https://muse.ai using local Chromium Termux engine and RainProxy US residential proxy.
Saves rendered screenshot, extracts DOM metadata, and checks authentication fields.
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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bridge import ProxyBridge, DEFAULT_PORT

CHROMIUM_BIN = os.environ.get("CHROMIUM_PATH") or "/data/data/com.termux/files/usr/bin/chromium-browser"
CHROMEDRIVER_BIN = os.environ.get("CHROMEDRIVER_PATH") or "/data/data/com.termux/files/usr/bin/chromedriver"


def run_browser(url="https://muse.ai", local_port=DEFAULT_PORT, headless=True):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    screenshot_file = os.path.join(base_dir, "muse_screenshot.png")
    html_file = os.path.join(base_dir, "page_source.html")

    print("=" * 60)
    print("  MUSE.AI CHROMIUM RUNNER (RAINPROXY US)")
    print(f"  Target URL : {url}")
    print(f"  Engine     : {CHROMIUM_BIN}")
    print(f"  Bridge     : 127.0.0.1:{local_port}")
    print("=" * 60)

    # Inisialisasi bridge in-process jika belum aktif
    bridge = ProxyBridge(local_port=local_port)
    bridge.start(daemon=True)
    time.sleep(0.5)

    opts = Options()
    if os.path.exists(CHROMIUM_BIN):
        opts.binary_location = CHROMIUM_BIN
    
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1366,768")
    opts.add_argument(f"--proxy-server=http://127.0.0.1:{local_port}")
    opts.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(executable_path=CHROMEDRIVER_BIN) if os.path.exists(CHROMEDRIVER_BIN) else None
    driver = webdriver.Chrome(service=service, options=opts) if service else webdriver.Chrome(options=opts)

    try:
        print(f"\n[*] Navigating to {url} via RainProxy US...")
        driver.get(url)

        # Tunggu elemen halaman terload
        time.sleep(3)
        current_url = driver.current_url
        page_title = driver.title

        print(f"[+] Loaded URL : {current_url}")
        print(f"[+] Page Title : {page_title}")

        # Simpan screenshot
        driver.save_screenshot(screenshot_file)
        print(f"[+] Screenshot : {screenshot_file}")

        # Simpan HTML
        html_content = driver.page_source
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"[+] Page Source: {html_file} ({len(html_content)} bytes)")

        # Deteksi elemen form & tombol
        inputs = driver.find_elements(By.TAG_NAME, "input")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        
        print("\n[*] Detected Inputs:")
        for idx, inp in enumerate(inputs):
            name = inp.get_attribute("name") or "(no name)"
            type_attr = inp.get_attribute("type") or "text"
            placeholder = inp.get_attribute("placeholder") or ""
            print(f"    [{idx+1}] type='{type_attr}' name='{name}' placeholder='{placeholder}'")

        print("\n[*] Detected Buttons:")
        for idx, btn in enumerate(buttons):
            text = btn.text.strip().replace("\n", " ")
            if text:
                print(f"    [{idx+1}] text='{text}'")

        return {
            "status": "success",
            "url": current_url,
            "title": page_title,
            "screenshot": screenshot_file,
            "html": html_file
        }

    except Exception as e:
        print(f"[-] Error: {e}", file=sys.stderr)
        return {"status": "error", "message": str(e)}
    finally:
        driver.quit()
        bridge.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Open muse.ai with Chromium via RainProxy US")
    parser.add_argument("--url", default="https://muse.ai", help="Target URL (default: https://muse.ai)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Bridge port")
    parser.add_argument("--no-headless", action="store_true", help="Disable headless mode")
    args = parser.parse_args()

    run_browser(url=args.url, local_port=args.port, headless=not args.no_headless)
