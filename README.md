# Canopy — GEE Repository Manager

A modern web app to browse and export your Google Earth Engine repositories.

## Stack
- **Backend**: FastAPI (Python) on port `8000`
- **Frontend**: Static HTML served on port `3000`
- No nginx, no reverse proxy — designed for use with Pangolin or Cloudflare Tunnel.

## Quick Start

```bash
docker compose up --build
```

Then open **http://localhost:3000** in your browser.

## Usage

### Step 1 — Authenticate
1. Open GEE Code Editor in Chrome/Brave
2. Open DevTools → Application → Cookies → `code.earthengine.google.com`
3. Copy all cookies into a Python dict format:
   ```python
   cookies = {
       "__Secure-BUCKET": "...",
       "SSID": "...",
       ...
   }
   ```
4. Find your XSRF token: DevTools → Network → any request → Headers → `x-xsrf-token`
5. Paste both into the app and click **Fetch Repositories**

### Step 2 — Select Repositories
- Filter by access level (owner / writer / reader)
- Search by name
- Select individual repos or use **Select all**

### Step 3 — Export JSON
- Click **Export JSON** in the floating bar
- Preview the prettified JSON output
- Copy to clipboard or download as a `.json` file

## Export Format

```json
{
  "apps": {
    "name": "users/samapriya/apps",
    "clone_url": "https://earthengine.googlesource.com/users/samapriya/apps"
  }
}
```

## Tunnel Setup

### Cloudflare Tunnel
Point your tunnel to `http://localhost:3000` for the frontend  
and optionally `http://localhost:8000` for the API.

### Pangolin
Configure your route to forward to `http://canopy-frontend:3000`  
and `http://canopy-backend:8000` respectively.

## Security Notes
- Cookies are **never stored** — they exist in browser memory only for the session
- The backend makes a single GET to `https://code.earthengine.google.com/repo/list`
- No database, no logging of credentials
