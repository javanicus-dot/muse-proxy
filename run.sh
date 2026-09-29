#!/usr/bin/env bash
# ==========================================================
#  MUSE.AI RUNNER SCRIPT (RAINPROXY US)
# ==========================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

ACTION="${1:-browser}"

case "$ACTION" in
  browser)
    echo "[+] Menjalankan Chromium Browser Runner ke muse.ai..."
    python3 "$DIR/open_browser.py" "${@:2}"
    ;;
  api)
    echo "[+] Menjalankan Direct TLS Client ke muse.ai..."
    python3 "$DIR/client_api.py" "${@:2}"
    ;;
  bridge)
    echo "[+] Menjalankan RainProxy US Local Bridge..."
    python3 "$DIR/bridge.py" "${@:2}"
    ;;
  refresh)
    echo "[+] Memperbarui daftar RainProxy US..."
    node /data/data/com.termux/files/home/rainproxy/generate.js --country US --check
    cp /data/data/com.termux/files/home/rainproxy/proxies.txt "$DIR/proxies.txt"
    echo "[+] Proxies updated di $DIR/proxies.txt"
    ;;
  *)
    echo "Usage: $0 {browser|api|bridge|refresh} [options]"
    exit 1
    ;;
esac
