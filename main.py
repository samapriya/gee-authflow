from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests

app = FastAPI(
    title="AuthFlow — GEE Repository Manager",
    description="Browse, filter, and export your Google Earth Engine repositories.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthPayload(BaseModel):
    cookies: dict
    xsrf_token: str


class ExportPayload(BaseModel):
    repos: list[str]
    cookies: dict
    xsrf_token: str


@app.get("/health", tags=["System"])
def health():
    """Returns ok if the service is running."""
    return {"status": "ok"}


@app.post("/api/repos", tags=["GEE"])
def list_repos(payload: AuthPayload):
    """
    Fetch the authenticated user's full repository list from GEE.
    Pass your browser session cookies and XSRF token from the GEE Code Editor.
    Expect 1–2 minutes — GEE's repo list endpoint is genuinely slow.
    """
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "dnt": "1",
        "priority": "u=1, i",
        "referer": "https://code.earthengine.google.com/",
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Brave";v="146"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36"
        ),
        "x-xsrf-token": payload.xsrf_token,
    }

    try:
        response = requests.get(
            "https://code.earthengine.google.com/repo/list",
            headers=headers,
            cookies=payload.cookies,
            timeout=180,
        )
    except requests.exceptions.ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach code.earthengine.google.com: {e}",
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Request timed out after 3 minutes — GEE may be overloaded, try again",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not response.ok:
        try:
            body = response.json()
        except Exception:
            body = response.text[:500]
        raise HTTPException(
            status_code=response.status_code,
            detail={
                "message": f"GEE returned HTTP {response.status_code}",
                "body": body,
                "hint": _hint(response.status_code),
            },
        )

    try:
        data = response.json()
    except Exception:
        raise HTTPException(
            status_code=502,
            detail=f"GEE returned non-JSON: {response.text[:300]}",
        )

    return {"repos": data}


def _hint(status: int) -> str:
    return {
        400: "Bad request — check XSRF token format",
        401: "Unauthorized — cookies may be expired",
        403: "Forbidden — cookies expired or XSRF token wrong",
        501: "Server rejected request",
        502: "Bad gateway from GEE",
        503: "GEE service unavailable",
    }.get(status, "Check the body field for details")


@app.post("/api/export", tags=["GEE"])
def export_repos(payload: ExportPayload):
    """
    Format a list of repo names into a structured export manifest with clone URLs.
    """
    result = {}
    for name in payload.repos:
        key = name.split("/")[-1]
        result[key] = {
            "name": name,
            "clone_url": f"https://earthengine.googlesource.com/{name}",
        }
    return result


# ── Serve the frontend — must be last so /docs and /api routes take priority ──
app.mount("/", StaticFiles(directory="static", html=True), name="static")
