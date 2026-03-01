import asyncio
import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from src.api.jobs import job_store
from src.api.models import (
    CollectJobRequest,
    AnalyzeJobRequest,
    InstagramLoginRequest,
    Instagram2FARequest,
    SaveKeysRequest,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths (relative to project root, resolved from this file's location)
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve()
PROJECT_ROOT = _HERE.parent.parent.parent
DOWNLOADS_DIR = PROJECT_ROOT / "downloads"
AUTH_DIR = PROJECT_ROOT / "auth"
SESSION_FILE = AUTH_DIR / "session.json"
ENV_FILE = AUTH_DIR / ".env"
INDEX_HTML = PROJECT_ROOT / "src" / "web" / "index.html"

# ---------------------------------------------------------------------------
# Instagram client cache
# ---------------------------------------------------------------------------
_insta_client = None
_insta_client_lock = threading.Lock()

# Pending logins: token -> {cl, username, password, created_at}
_pending_login: Dict[str, dict] = {}
_pending_login_lock = threading.Lock()


def _get_cached_insta_client():
    """Return the cached Instagram client, or None if not available."""
    return _insta_client


def _invalidate_insta_client():
    global _insta_client
    with _insta_client_lock:
        _insta_client = None


def _evict_old_pending():
    now = time.time()
    with _pending_login_lock:
        expired = [t for t, v in _pending_login.items() if now - v["created_at"] > 600]
        for t in expired:
            del _pending_login[t]


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="ReelScout")


# ---------------------------------------------------------------------------
# Static routes
# ---------------------------------------------------------------------------
@app.get("/")
async def index():
    if not INDEX_HTML.is_file():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(str(INDEX_HTML))


@app.get("/media/{collection}/{path:path}")
async def serve_media(collection: str, path: str):
    file_path = DOWNLOADS_DIR / collection / path
    # For carousels (directory), serve the first file
    if file_path.is_dir():
        children = sorted(file_path.iterdir())
        if not children:
            raise HTTPException(status_code=404, detail="Empty carousel directory")
        file_path = children[0]
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Media file not found")
    return FileResponse(str(file_path))


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
@app.get("/api/auth/status")
async def auth_status():
    instagram = SESSION_FILE.is_file()
    gemini_key = False
    maps_key = False
    if ENV_FILE.is_file():
        # Parse .env manually to avoid side effects
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY=") and len(line) > len("GEMINI_API_KEY="):
                gemini_key = True
            if line.startswith("GOOGLE_PLACES_API=") and len(line) > len("GOOGLE_PLACES_API="):
                maps_key = True
    # Also check current environment (already loaded by modules)
    if os.getenv("GEMINI_API_KEY"):
        gemini_key = True
    if os.getenv("GOOGLE_PLACES_API"):
        maps_key = True
    return {"instagram": instagram, "gemini_key": gemini_key, "maps_key": maps_key}


@app.post("/api/auth/keys")
async def save_keys(body: SaveKeysRequest):
    AUTH_DIR.mkdir(exist_ok=True)
    try:
        from dotenv import set_key
        ENV_FILE.touch()
        if body.gemini_api_key:
            set_key(str(ENV_FILE), "GEMINI_API_KEY", body.gemini_api_key)
            os.environ["GEMINI_API_KEY"] = body.gemini_api_key
        if body.google_places_api:
            set_key(str(ENV_FILE), "GOOGLE_PLACES_API", body.google_places_api)
            os.environ["GOOGLE_PLACES_API"] = body.google_places_api
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/instagram/login")
async def instagram_login(body: InstagramLoginRequest):
    _evict_old_pending()
    from instagrapi import Client
    from instagrapi.exceptions import TwoFactorRequired, BadPassword, ChallengeRequired, ClientError

    cl = Client()
    cl.delay_range = [1, 3]
    try:
        cl.login(body.username, body.password)
        AUTH_DIR.mkdir(exist_ok=True)
        cl.dump_settings(str(SESSION_FILE))
        _invalidate_insta_client()
        return {"status": "ok"}
    except TwoFactorRequired:
        token = str(uuid.uuid4())[:8]
        with _pending_login_lock:
            _pending_login[token] = {
                "cl": cl,
                "username": body.username,
                "password": body.password,
                "created_at": time.time(),
            }
        return {"status": "2fa_required", "token": token}
    except BadPassword:
        return {"status": "error", "message": "Incorrect username or password"}
    except ChallengeRequired as e:
        return {"status": "error", "message": f"Challenge required: {e}"}
    except ClientError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/instagram/2fa")
async def instagram_2fa(body: Instagram2FARequest):
    _evict_old_pending()
    with _pending_login_lock:
        pending = _pending_login.get(body.token)
    if not pending:
        return {"status": "error", "message": "Invalid or expired 2FA session"}

    from instagrapi.exceptions import BadPassword, ChallengeRequired, ClientError

    cl = pending["cl"]
    try:
        cl.login(pending["username"], pending["password"], verification_code=body.code)
        AUTH_DIR.mkdir(exist_ok=True)
        cl.dump_settings(str(SESSION_FILE))
        _invalidate_insta_client()
        with _pending_login_lock:
            _pending_login.pop(body.token, None)
        return {"status": "ok"}
    except BadPassword:
        return {"status": "error", "message": "Incorrect 2FA code or password"}
    except ChallengeRequired as e:
        return {"status": "error", "message": f"Challenge required: {e}"}
    except ClientError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/auth/instagram/session")
async def delete_instagram_session():
    if SESSION_FILE.is_file():
        SESSION_FILE.unlink()
    _invalidate_insta_client()
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Collection endpoints
# ---------------------------------------------------------------------------
@app.get("/api/collections/instagram")
async def list_instagram_collections():
    """Return Instagram saved collections using cached client."""
    global _insta_client
    from src.instagram_client import InstagramClient

    with _insta_client_lock:
        if _insta_client is None or not _insta_client.logged_in:
            if not SESSION_FILE.is_file():
                raise HTTPException(status_code=401, detail="Not logged in to Instagram")
            cl = InstagramClient(session_file=SESSION_FILE)
            if not cl.login():
                raise HTTPException(status_code=401, detail="Instagram session invalid")
            _insta_client = cl

    collections = _insta_client.get_collections()
    if collections is None:
        raise HTTPException(status_code=500, detail="Failed to fetch collections")
    return [{"id": str(c.id), "name": c.name} for c in collections]


@app.get("/api/collections/local")
async def list_local_collections():
    """Return names of locally downloaded collections (those with metadata.json)."""
    if not DOWNLOADS_DIR.is_dir():
        return []
    return [
        d.name
        for d in sorted(DOWNLOADS_DIR.iterdir())
        if d.is_dir() and (d / "metadata.json").is_file()
    ]


# ---------------------------------------------------------------------------
# Job endpoints
# ---------------------------------------------------------------------------
@app.post("/api/jobs/collect")
async def start_collect(body: CollectJobRequest):
    job = job_store.create("collect")
    job.status = "running"

    def _run():
        try:
            from src.pipeline import run_collect_pipeline

            result = run_collect_pipeline(
                collection_id=body.collection_id,
                collection_name=body.collection_name,
                download_dir=DOWNLOADS_DIR,
                session_file=SESSION_FILE,
                skip_download=body.skip_download,
                progress_callback=job.add_event,
            )
            job.result = result
            job.status = "done"
        except Exception as e:
            logger.exception("Collect pipeline error")
            job.error = str(e)
            job.status = "error"

    threading.Thread(target=_run, daemon=True).start()
    return {"job_id": job.job_id}


@app.post("/api/jobs/analyze")
async def start_analyze(body: AnalyzeJobRequest):
    job = job_store.create("analyze")
    job.status = "running"

    def _run():
        try:
            from src.pipeline import run_analyze_pipeline

            result = run_analyze_pipeline(
                collection_name=body.collection_name,
                download_dir=DOWNLOADS_DIR,
                progress_callback=job.add_event,
            )
            job.result = result
            job.status = "done"
        except Exception as e:
            logger.exception("Analyze pipeline error")
            job.error = str(e)
            job.status = "error"

    threading.Thread(target=_run, daemon=True).start()
    return {"job_id": job.job_id}


@app.get("/api/jobs/{job_id}/status")
async def job_status(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@app.get("/api/jobs/{job_id}/stream")
async def job_stream(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def _generate():
        sent = 0
        while True:
            events = job.events
            if len(events) > sent:
                for event in events[sent:]:
                    yield f"data: {json.dumps(event)}\n\n"
                sent = len(events)

            if job.status in ("done", "error"):
                payload = {
                    "status": job.status,
                    "result": job.result,
                    "error": job.error,
                }
                yield f"event: done\ndata: {json.dumps(payload)}\n\n"
                break

            await asyncio.sleep(0.25)

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Results endpoint
# ---------------------------------------------------------------------------
@app.get("/api/results/{collection}")
async def get_results(collection: str):
    metadata_path = DOWNLOADS_DIR / collection / "metadata.json"
    if not metadata_path.is_file():
        raise HTTPException(status_code=404, detail="No metadata found for collection")
    with open(metadata_path, "r") as f:
        return json.load(f)
