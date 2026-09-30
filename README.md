# Meta Muse.ai OpenAI-Compatible Reverse Proxy

High-performance, ultra-lightweight multi-account OpenAI-compatible API reverse proxy for Meta Muse.ai (`muse-spark-1.3`), powered by headless Chromium via Patchright.

## Features

- **OpenAI Standard Compatibility**: Supports `/v1/chat/completions` (streaming & non-streaming) and `/v1/models`.
- **Ultra-Lightweight Engine**: Images, fonts, and marketing trackers are blocked at the native engine level (`imagesEnabled=false`, compact 800x600 viewport), consuming only ~30 MB RAM per context.
- **Multi-Account Load Balancing**: Automatically rotates requests across accounts listed in `cookies.txt` using Round-Robin.
- **Failover & Fault Tolerance**: Automatically reroutes requests to the next account if an account encounters an error or rate limit.
- **Auto Session Purge & Hygiene**: Automatically cleans chat sessions every 20 requests to prevent memory leaks and keep accounts completely clean.
- **Hot-Reloading**: Automatically detects modifications to `cookies.txt` without restarting the process.
- **Zero External Proxy Needed**: Connects directly to Muse.ai with native browser stealth.
- **Real Capacity Specs**: Configured for 350,000 tokens context window and 4,096 max completion tokens.

## Architecture

```
OpenAI Client / 9Router / Hermes / Cline / Cursor
                   │
                   ▼  (HTTP POST /v1/chat/completions)
          [ Muse Proxy Server ]  (Port 20133)
                   │
         [ Dedicated Worker Thread ]
         ├── Context #0 (Account 1 - Chromium Tab, 800x600, No Images)
         ├── Context #1 (Account 2 - Chromium Tab, 800x600, No Images)
         └── Context #N ...
                   │
                   ▼  (Direct HTTPS)
             https://muse.ai/
```

## Repository Structure

```
muse-proxy/
├── server.py              # Main ultra-lightweight reverse proxy server
├── cookies.example.txt    # Example template for multi-account cookies
├── requirements.txt       # Python dependencies
├── README.md              # Project documentation
└── tools/                 # Account creation, OTP, and verification automation scripts
    ├── register_muse.py
    ├── fb_register.py
    ├── auth_meta_and_verify.py
    ├── solve_fb_and_link.py
    ├── oauth_link.py
    ├── tempmail_api.py
    └── ...
```

## Quick Start

### 1. Requirements

- Python 3.10+
- Patchright (Chromium headless)

```bash
pip install -r requirements.txt
patchright install chromium
```

### 2. Configure Cookies

Copy `cookies.example.txt` to `cookies.txt`:

```bash
cp cookies.example.txt cookies.txt
```

Paste your browser cookies into `cookies.txt` (one line per account):

```text
# Account 1
datr=xxx; hatch_native_auth_device=xxx; hatch_sess=xxx; hatch_gw=xxx;

# Account 2
datr=yyy; hatch_native_auth_device=yyy; hatch_sess=yyy; hatch_gw=yyy;
```

### 3. Run the Server

```bash
python3 server.py
```

The server listens on `127.0.0.1:20133` by default. Set `MUSE_PROXY_HOST` and `MUSE_PROXY_PORT` to change the bind address and port. If 9Router runs in Docker, bind to the host's Docker bridge gateway address and use that address in 9Router's provider Base URL. The proxy has no API-key check, so do not expose its port to untrusted networks.

Or using PM2 for background daemon management:

```bash
pm2 start server.py --name muse-proxy --interpreter python3
```

## API Endpoints

### 1. Chat Completions (`POST /v1/chat/completions`)

Standard OpenAI payload:

```bash
curl http://127.0.0.1:20133/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "muse-spark-1.3",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

### 2. List Models (`GET /v1/models`)

```bash
curl http://127.0.0.1:20133/v1/models
```

### Image understanding with Chat Completions

Send an image in a `user` message as an OpenAI `image_url` content part. The proxy accepts base64 data URLs for JPEG, PNG, GIF, and WebP, with up to four images of 10 MB each per request. It uploads the image bytes through the Muse browser composer before sending the text prompt.

```json
{
  "model": "muse-spark-1.3",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "What is in this picture?"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,<BASE64_PNG_BYTES>"}}
      ]
    }
  ],
  "stream": false
}
```

Use an actual base64 string in place of `<BASE64_PNG_BYTES>`. Remote image URLs and file IDs are not supported. If the Muse page has no image upload control, the request fails rather than sending a text-only prompt. The browser automation depends on Muse's current page layout, so verify one image request with your account before relying on it. Image token usage is omitted because this proxy cannot count it accurately.

When routing through 9Router, configure the custom model as vision-capable and test an image request through 9Router itself. Some 9Router versions can hide image input or route it to another model based on the model's capability settings.

### 3. Health & Pool Status (`GET /health`)

```bash
curl http://127.0.0.1:20133/health
```

Returns pool status:

```json
{
  "status": "ok",
  "provider": "muse-spark-1.3",
  "models": ["muse-spark-1.3"],
  "pool": {
    "total_accounts": 2,
    "active_accounts": 2,
    "accounts": [
      {"index": 0, "active": true, "total_requests": 14, "session_requests": 4, "consecutive_errors": 0},
      {"index": 1, "active": true, "total_requests": 13, "session_requests": 3, "consecutive_errors": 0}
    ]
  }
}
```

### 4. Hot Reload Cookies (`POST /reload` or `GET /reload`)

```bash
curl http://127.0.0.1:20133/reload
```

### 5. Instant Session & Cache Purge (`POST /reset` or `GET /reset`)

Clears all conversation memory, wipes browser session caches, and returns all account tabs to fresh blank states:

```bash
curl http://127.0.0.1:20133/reset
```
