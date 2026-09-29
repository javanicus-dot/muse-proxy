#!/usr/bin/env python3
"""
RainProxy US Local HTTP/CONNECT Bridge (High-Reliability Multi-Proxy Fallback)
"""

import sys
import os
import socket
import select
import threading
import base64
import time

DEFAULT_PORT = 18899
DEFAULT_PROXIES_FILE = os.path.join(os.path.dirname(__file__), "proxies.txt")


def load_proxies(file_path=DEFAULT_PROXIES_FILE):
    proxies = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            proxies = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    if not proxies:
        proxies = ["udx48zcizqw-country-US-state-new_jersey-city-jerseycity-speed-fast-quality-high:bxrlw1p5csou@resi-bridge-us.rainproxy.io:3333"]
    return proxies


def parse_proxy(proxy_str):
    if "://" in proxy_str:
        proxy_str = proxy_str.split("://", 1)[1]
    auth_part, host_part = proxy_str.split("@", 1)
    user, passwd = auth_part.split(":", 1)
    host, port_s = host_part.split(":", 1)
    return host, int(port_s), user, passwd


class ProxyBridge:
    def __init__(self, local_port=DEFAULT_PORT, proxies=None):
        self.local_port = local_port
        self.proxies = proxies or load_proxies()
        self.current_idx = 0
        self.server_sock = None
        self.running = False

    def get_current_upstream(self):
        p_str = self.proxies[self.current_idx % len(self.proxies)]
        host, port, user, passwd = parse_proxy(p_str)
        token = base64.b64encode(f"{user}:{passwd}".encode()).decode()
        header = f"Proxy-Authorization: Basic {token}\r\n".encode()
        return host, port, header, user

    def rotate_upstream(self):
        self.current_idx = (self.current_idx + 1) % len(self.proxies)
        host, port, _, user = self.get_current_upstream()
        print(f"[*] Rotated upstream to proxy [{self.current_idx}]: {host}:{port} ({user[:25]}...)")

    def start(self, daemon=False):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(("127.0.0.1", self.local_port))
        self.server_sock.listen(256)
        self.running = True

        host, port, _, user = self.get_current_upstream()
        print(f"[*] RainProxy US Bridge running on 127.0.0.1:{self.local_port}")
        print(f"[*] Upstream Gateway: {host}:{port} ({user[:30]}...)")

        if daemon:
            t = threading.Thread(target=self._accept_loop, daemon=True)
            t.start()
            return t
        else:
            self._accept_loop()

    def _accept_loop(self):
        while self.running:
            try:
                client_sock, addr = self.server_sock.accept()
                threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True).start()
            except Exception as e:
                if not self.running:
                    break
                time.sleep(0.1)

    def _handle_client(self, client_sock):
        upstream_sock = None
        try:
            req_data = b""
            client_sock.settimeout(15.0)
            while b"\r\n\r\n" not in req_data:
                chunk = client_sock.recv(4096)
                if not chunk:
                    break
                req_data += chunk
            if not req_data:
                client_sock.close()
                return

            host, port, auth_header, _ = self.get_current_upstream()
            connected = False
            for attempt in range(2):
                try:
                    upstream_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    upstream_sock.settimeout(12.0)
                    upstream_sock.connect((host, port))
                    connected = True
                    break
                except Exception:
                    self.rotate_upstream()
                    host, port, auth_header, _ = self.get_current_upstream()

            if not connected:
                client_sock.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                client_sock.close()
                return

            header_end = req_data.find(b"\r\n")
            first_line = req_data[:header_end + 2]
            rest = req_data[header_end + 2:]
            modified_req = first_line + auth_header + rest

            is_connect = req_data.startswith(b"CONNECT ")
            if is_connect:
                upstream_sock.sendall(modified_req)
                resp = b""
                while b"\r\n\r\n" not in resp:
                    chunk = upstream_sock.recv(4096)
                    if not chunk:
                        break
                    resp += chunk
                client_sock.sendall(resp)
                if b" 200 " not in resp:
                    client_sock.close()
                    upstream_sock.close()
                    return
            else:
                upstream_sock.sendall(modified_req)

            client_sock.settimeout(None)
            upstream_sock.settimeout(None)

            sockets = [client_sock, upstream_sock]
            while True:
                rlist, _, xlist = select.select(sockets, [], sockets, 60.0)
                if xlist or not rlist:
                    break
                for s in rlist:
                    other = upstream_sock if s is client_sock else client_sock
                    try:
                        data = s.recv(16384)
                        if not data:
                            return
                        other.sendall(data)
                    except Exception:
                        return
        except Exception:
            pass
        finally:
            if client_sock:
                try: client_sock.close()
                except: pass
            if upstream_sock:
                try: upstream_sock.close()
                except: pass

    def stop(self):
        self.running = False
        if self.server_sock:
            try: self.server_sock.close()
            except: pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    bridge = ProxyBridge(local_port=port)
    try:
        bridge.start(daemon=False)
    except KeyboardInterrupt:
        bridge.stop()
        print("\n[+] Bridge stopped.")
