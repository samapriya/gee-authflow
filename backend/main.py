from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI(title="GEE Repo Tool API")

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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/repos")
def list_repos(payload: AuthPayload):
    # Exact headers from the working Python script.
    # GEE is just slow (1-2 min) — that's normal, not a header issue.
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
            timeout=180,  # GEE legitimately takes 1-2 minutes
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


@app.post("/api/export")
def export_repos(payload: ExportPayload):
    result = {}
    for name in payload.repos:
        key = name.split("/")[-1]
        result[key] = {
            "name": name,
            "clone_url": f"https://earthengine.googlesource.com/{name}",
        }
    return result
