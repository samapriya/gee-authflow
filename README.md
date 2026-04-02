# AuthFlow — GEE Repository Manager

![AuthFlow](https://i.imgur.com/sf5QL1g.png)

> Browse, filter, and export your Google Earth Engine repositories with secure, session-based authentication. No database. No stored credentials. Just your session, your repos, and a clean JSON export.

---

## What It Does

AuthFlow is a lightweight two-container web app that connects to the [Google Earth Engine Code Editor](https://code.earthengine.google.com/) using your browser session cookies and XSRF token. It lets you:

- **Fetch** your full GEE repository list across all access levels (owner / writer / reader)
- **Browse** repos in a polished grid or list view with live search and filter
- **Select** individual repositories or use bulk selection
- **Export** a structured JSON manifest with clone URLs, optionally including access level metadata

No OAuth dance. No API keys. AuthFlow piggybacks on your existing authenticated GEE session — the same way your browser does — and discards everything the moment you close the tab.

---

## Stack

| Layer | Technology | Port |
|---|---|---|
| Backend | FastAPI (Python) | `8432` (host) → `8000` (container) |
| Frontend | Static HTML/CSS/JS | `127.0.0.1:55432` (host) → `3000` (container) |

- **No nginx.** No reverse proxy required.
- Designed for use behind [Pangolin](https://github.com/fosrl/pangolin) or a Cloudflare Tunnel.
- Frontend is bound to `127.0.0.1` only — it won't be exposed to your network without a tunnel.

---

## Quick Start

```bash
docker compose up --build
```

Then open **http://localhost:55432** in your browser.

---

## How to Use

### Step 1 — Authenticate

AuthFlow needs your live GEE session to talk to `code.earthengine.google.com`. Here's how to grab what it needs:

1. Open the [GEE Code Editor](https://code.earthengine.google.com/) in Chrome or Brave
2. Open **DevTools** (`F12`) → **Application** → **Cookies** → `code.earthengine.google.com`
3. Copy the cookies into a Python-style dict:

```python
{
    "__Secure-BUCKET": "...",
    "SSID": "...",
    "SID": "...",
    "HSID": "..."
}
```

4. Find your XSRF token: **DevTools → Network** → click any request → **Headers** → look for `x-xsrf-token`
5. Paste both into the AuthFlow auth panel and click **Fetch Repositories**

> ⏳ **Heads up:** GEE's repo list endpoint is genuinely slow — expect 1–2 minutes. The backend waits up to 3 minutes before timing out. This is normal GEE behaviour, not a bug.

---

### Step 2 — Browse & Select

Once loaded, you land in the repository browser:

- **Sidebar** shows a live count of all repos broken down by access level
- **Filter** by `owner`, `writer`, or `reader` using the sidebar filter list
- **Search** by repo name using the search bar
- **Toggle** between grid view (cards) and list view (rows)
- **Select** repos individually by clicking, or use **Select All** / **Deselect All** in the toolbar
- A floating action bar appears at the bottom as soon as you've selected at least one repo

---

### Step 3 — Export JSON

Click **Export JSON** in the floating bar to generate your manifest:

- Preview the prettified, syntax-highlighted JSON output
- Toggle the **Include ownership** switch to add `access` fields to each entry
- **Copy** to clipboard or **Download** as a `.json` file

#### Export Format (without ownership)

```json
{
  "apps": {
    "name": "users/samapriya/apps",
    "clone_url": "https://earthengine.googlesource.com/users/samapriya/apps"
  },
  "scripts": {
    "name": "users/samapriya/scripts",
    "clone_url": "https://earthengine.googlesource.com/users/samapriya/scripts"
  }
}
```

#### Export Format (with ownership)

```json
{
  "apps": {
    "name": "users/samapriya/apps",
    "clone_url": "https://earthengine.googlesource.com/users/samapriya/apps",
    "access": "owner"
  }
}
```

The JSON key for each repo is the short name (last path segment). The `clone_url` points to Google's Earthengine Gitiles instance and can be used directly with `git clone`.

---

## API Reference

The FastAPI backend exposes two endpoints.

### `GET /health`

Returns `{"status": "ok"}`. Used to confirm the backend is running.

---

### `POST /api/repos`

Fetches the authenticated user's full repository list from GEE.

**Request body:**
```json
{
  "cookies": { "__Secure-BUCKET": "...", "SSID": "..." },
  "xsrf_token": "your-token-here"
}
```

**Response:**
```json
{
  "repos": [ ... ]
}
```

**Error hints:**

| HTTP Status | Likely Cause |
|---|---|
| `401` | Cookies are expired — re-grab from DevTools |
| `403` | Cookies expired or XSRF token is wrong |
| `504` | GEE timed out — it's overloaded, try again |
| `502` | GEE returned non-JSON (rare) |

---

### `POST /api/export`

Formats a list of repo names into the export manifest structure. In practice the frontend builds this client-side, but the endpoint is available for scripting use.

**Request body:**
```json
{
  "repos": ["users/samapriya/apps", "users/samapriya/scripts"],
  "cookies": { ... },
  "xsrf_token": "..."
}
```

---

## Docker Compose Details

```yaml
services:
  backend:
    build: ./backend
    container_name: canopy-backend
    ports:
      - "8432:8000"         # backend accessible at localhost:8432
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: canopy-frontend
    ports:
      - "127.0.0.1:55432:3000"   # frontend only on loopback — use a tunnel to expose
    depends_on:
      - backend
    restart: unless-stopped
```

The internal container names (`canopy-backend`, `canopy-frontend`) are used when configuring tunnel routes.

---

## Tunnel Setup

### Cloudflare Tunnel

Point your tunnel to:
- `http://localhost:55432` — frontend UI
- `http://localhost:8432` — backend API (optional, if you want direct API access)

### Pangolin

Configure your routes to forward to:
- `http://canopy-frontend:3000` — frontend
- `http://canopy-backend:8000` — backend

---

## Security Notes

- **Credentials are never stored.** Cookies and XSRF tokens live only in your browser's memory for the duration of the session.
- The backend makes a single outbound GET to `https://code.earthengine.google.com/repo/list` using your provided session headers — nothing else.
- There is no database, no logging of credentials, and no server-side session state.
- The frontend is bound to `127.0.0.1` by default — it cannot be reached from outside your machine without explicitly exposing it through a tunnel.
- CORS is open (`allow_origins=["*"]`) on the backend, which is fine for a local-only tool. Tighten this if you expose the API publicly.
