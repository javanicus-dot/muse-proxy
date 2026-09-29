#!/usr/bin/env python3
"""
TempMail API Client for mail.berkahkita49.biz.id / api.berkahkita49.biz.id
"""

import time
import re
import json
import urllib.request
import urllib.parse
import sys

API_BASE = "https://api.berkahkita49.biz.id"
DEFAULT_DOMAIN = "berkahkita49.biz.id"


class BerkahTempMail:
    def __init__(self, api_base=API_BASE):
        self.api_base = api_base.rstrip("/")

    def get_domains(self):
        req = urllib.request.Request(f"{self.api_base}/fe/v1/domains")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("domains", [DEFAULT_DOMAIN])

    def create_inbox(self, domain=DEFAULT_DOMAIN, name=None):
        payload = {"domain": domain}
        if name:
            payload["name"] = name
        req = urllib.request.Request(
            f"{self.api_base}/fe/v1/inbox",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return {
                "address": data.get("address"),
                "session": data.get("session"),
                "expires_at": data.get("expires_at"),
            }

    def get_messages(self, address, session=None):
        # 1. Coba session Bearer
        if session:
            try:
                req = urllib.request.Request(
                    f"{self.api_base}/fe/v1/messages",
                    headers={"Authorization": f"Bearer {session}"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                    if "messages" in data:
                        return data["messages"]
            except Exception:
                pass

        # 2. Fallback ke /emails/:address + /inbox/:id
        try:
            req = urllib.request.Request(f"{self.api_base}/emails/{urllib.parse.quote(address)}")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                items = data.get("result", [])
                detailed = []
                for it in items[:5]:
                    msg_id = it.get("id")
                    if not msg_id:
                        continue
                    try:
                        ireq = urllib.request.Request(f"{self.api_base}/inbox/{msg_id}")
                        with urllib.request.urlopen(ireq, timeout=10) as iresp:
                            idata = json.loads(iresp.read().decode())
                            m = idata.get("result", {})
                            code = m.get("code")
                            if not code:
                                body = (m.get("html_content") or "") + " " + (m.get("text_content") or "")
                                match = re.search(r"\b(\d{6})\b", body)
                                if match:
                                    code = match.group(1)
                            detailed.append({
                                "id": msg_id,
                                "from": m.get("from_address") or it.get("from_address"),
                                "subject": m.get("subject") or it.get("subject"),
                                "code": code,
                                "link": m.get("link"),
                                "received_at": m.get("received_at"),
                            })
                    except Exception:
                        pass
                return detailed
        except Exception:
            return []

    def wait_for_code(self, address, session=None, timeout=120, poll_interval=3):
        print(f"[*] Menunggu kode verifikasi untuk {address} (Timeout: {timeout}s)...")
        start = time.time()
        while time.time() - start < timeout:
            msgs = self.get_messages(address, session)
            for m in msgs:
                code = m.get("code")
                if code:
                    print(f"[✅] KODE DITERIMA: {code} (Subject: {m.get('subject')})")
                    return code, m
            time.sleep(poll_interval)
        print("[-] Timeout: Kode tidak masuk dalam batas waktu.")
        return None, None


if __name__ == "__main__":
    client = BerkahTempMail()
    inbox = client.create_inbox()
    print("Inbox baru dibuat:", inbox)
