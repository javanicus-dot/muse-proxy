#!/usr/bin/env python3
"""
Muse.ai Fast TLS API & HTTP Client (curl_cffi with Chrome Fingerprint)
Connects directly via RainProxy US upstream proxy.
"""

import os
import sys
import json
from bs4 import BeautifulSoup
from curl_cffi import requests

from bridge import load_proxy


def get_proxy_url():
    raw = load_proxy()
    if not raw.startswith("http://") and not raw.startswith("socks5://"):
        return f"http://{raw}"
    return raw


def fetch_muse(url="https://muse.ai"):
    proxy_url = get_proxy_url()
    print("=" * 60)
    print("  MUSE.AI DIRECT TLS CLIENT (CURL_CFFI)")
    print(f"  Target URL : {url}")
    print(f"  Proxy      : {proxy_url.split('@')[-1]} (Residential US)")
    print("=" * 60)

    proxies = {"http": proxy_url, "https": proxy_url}
    session = requests.Session(impersonate="chrome120")
    
    # 1. Test Proxy IP
    print("\n[*] Verifying Proxy Exit IP...")
    try:
        ip_res = session.get("https://ipinfo.io/json", proxies=proxies, timeout=15)
        ip_data = ip_res.json()
        print(f"[+] Proxy IP: {ip_data.get('ip')} | {ip_data.get('city')}, {ip_data.get('region')} ({ip_data.get('country')}) | ISP: {ip_data.get('org')}")
    except Exception as e:
        print(f"[-] IP probe failed: {e}")

    # 2. Fetch muse.ai
    print(f"\n[*] Requesting {url}...")
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Upgrade-Insecure-Requests": "1"
    }

    res = session.get(url, headers=headers, proxies=proxies, allow_redirects=True, timeout=20)
    print(f"[+] Final Status : {res.status_code}")
    print(f"[+] Final URL    : {res.url}")
    print(f"[+] HTTP Version : {res.http_version}")

    # Cookies
    try:
        print("\n[*] Session Cookies:")
        for cookie in session.cookies.jar:
            print(f"    - {cookie.name} ({cookie.domain}): {cookie.value[:30]}...")
    except Exception as e:
        print(f"    - (error reading cookies: {e})")

    # HTML parsing
    soup = BeautifulSoup(res.text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else "(No Title)"
    print(f"\n[+] Title: {title}")

    # Sections
    headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"]) if h.get_text(strip=True)]
    print("\n[*] Page Headings:")
    for h in headings[:8]:
        print(f"    • {h}")

    # Save output
    base_dir = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(base_dir, "response.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(res.text)
    print(f"\n[+] Saved HTML to {out_file} ({len(res.text)} bytes)")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://muse.ai"
    fetch_muse(target)
