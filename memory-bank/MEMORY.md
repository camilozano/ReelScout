# ReelScout - Project Memory

## Overview
A tool to collect Instagram Reels from saved collections, analyze them with Gemini AI to extract location data, enrich with Google Maps, and display results in a web UI. The user's collections are primarily travel content.

## Key Files
- `reel_scout_cli.py` — CLI entrypoint (click): `collect`, `analyze`, `serve` commands
- `src/pipeline.py` — extracted pipeline logic: `run_analyze_pipeline()`, `run_collect_pipeline()` with `progress_callback`
- `src/ai_analyzer.py` — Gemini AI integration (AIAnalyzer class)
- `src/downloader.py` — Downloads media (video/photo/carousel) + writes metadata.json
- `src/instagram_client.py` — instagrapi login + collection/media fetching
- `src/location_enricher.py` — Google Maps Places API enrichment
- `src/api/__init__.py` — empty package marker
- `src/api/app.py` — FastAPI app: all routes, SSE streaming, auth endpoints, job runner
- `src/api/jobs.py` — thread-safe in-memory JobStore (pending→running→done|error)
- `src/api/models.py` — Pydantic request models for API
- `src/web/index.html` — single-file frontend (Tailwind CDN + Inter font + vanilla JS)
- `memory-bank/` — Project documentation (Plans.md, progress.md, activeContext.md, etc.)
- `tests/` — pytest unit tests for all modules

## Tech Stack
- Python 3.11 (system), Poetry 2.3.2 — run via `/home/camilozano/.local/bin/poetry`
- `instagrapi` 2.3.0 — unofficial Instagram API
- `google-genai` (NOT `google-generativeai`) — Gemini API client
- `googlemaps` — Google Maps Places API
- `click` — CLI framework
- `pydantic` 2.12.5 — schema validation
- `python-dotenv` — loads `auth/.env`
- `fastapi ^0.134.0` + `uvicorn[standard] ^0.41.0` — web server

## Environment (this machine)
- OS: Debian 12 (Bookworm) on Synology NAS
- Poetry: `/home/camilozano/.local/bin/poetry`
- Run CLI: `poetry run reel-scout collect` from `/volume2/nixhome/code/ReelScout`
- Run web UI: `poetry run reel-scout serve --port 8001` (port 8000 is taken by Docker)
- Python 3.13 not available via apt — using 3.11, pyproject.toml set to `^3.11`

## Configuration
- Instagram session: `auth/session.json`
- API keys in `auth/.env`: `GEMINI_API_KEY`, `GOOGLE_PLACES_API`

## Current Gemini Model & Prompt
- Text analysis: `gemini-3-flash-preview` (DEFAULT_MODEL_NAME in AIAnalyzer)
- Uses `genai.Client(api_key=...)` + `client.models.generate_content()`
- JSON mode: `response_mime_type="application/json"`, `response_schema=LocationResponse`
- Pydantic `LocationResponse`: `{location_found: bool, locations: Optional[List[str]]}`
- Prompt focuses on Google Maps search query formatting: "Sagrada Família, Barcelona" style.
  Handles 📍 pins, hashtags, @-tagged places. Ignores vague references.

## Web UI Architecture
- `GET /` serves `src/web/index.html`
- `GET /media/{collection}/{path:path}` serves downloaded files; for carousels (dirs) serves first file
- Auth routes: `GET /api/auth/status`, `POST /api/auth/keys`, `POST /api/auth/instagram/login`,
  `POST /api/auth/instagram/2fa`, `DELETE /api/auth/instagram/session`
- Collection routes: `GET /api/collections/instagram`, `GET /api/collections/local`
- Job routes: `POST /api/jobs/collect`, `POST /api/jobs/analyze`,
  `GET /api/jobs/{id}/status`, `GET /api/jobs/{id}/stream` (SSE)
- Results: `GET /api/results/{collection}` → full metadata.json
- Background jobs use `threading.Thread(daemon=True)` (correct for blocking sync libs)
- Instagram client cached module-level in app.py; invalidated on session changes
- Pending 2FA logins stored in `_pending_login` dict, evicted after 10 minutes
- PROJECT_ROOT resolved from `Path(__file__)` in app.py — not cwd-dependent

## Data Flow
1. `collect`: Login → pick collection → download media + write `downloads/{collection}/metadata.json`
2. `analyze`: Read metadata.json → Phase 1: AI caption analysis → Phase 2: Google Maps enrichment → write back to metadata.json

## metadata.json Structure (per item)
```json
{
  "relative_path": "filename.mp4 | pk/ (carousel) | null",
  "caption": "...",
  "url": "https://www.instagram.com/p/{code}/",
  "pk": 12345,
  "media_type": 1|2|8,
  "product_type": "...",
  "caption_analysis": {"location_found": bool, "locations": [...], "error": "..."},
  "google_maps_enrichment": [{"original_name": "...", "google_maps_data": {...}, "error": null}]
}
```

## Media Types
- 1 = Photo (downloads as jpg)
- 2 = Video / Reel (downloads as mp4) — 9:16 portrait aspect ratio
- 8 = Carousel (creates `{pk}/` subdir, downloads individual resources)

## Frontend Notes
- 4 tabs: Setup, Collect, Analyze, Results
- Setup tab auto-opens on load if any auth piece missing
- Collect tab: Instagram collections dropdown + SSE progress bar
- Analyze tab: local collections dropdown + dual progress bars (analyze / enrich phases)
- Results tab: table with inline video/image previews, Google Maps links, status badges
- Video previews: 160px wide, natural height (no forced aspect-ratio container — avoids browser rendering bugs), `preload="metadata"`, play button overlay fades on play
- Photos: 160px wide, natural height

## Multi-User Support (IMPLEMENTED)
- Sessions stored in `auth/sessions/{username}.json` (SESSIONS_DIR = AUTH_DIR / "sessions")
- Downloads stored in `downloads/{username}/{collection}/`
- Auto-migration: `_run_migration()` in app.py runs on startup via `lifespan` context; also `reel-scout migrate` CLI command
- Per-user client cache: `_insta_clients: Dict[str, object]` keyed by username
- `GET /api/auth/users` → list users; `DELETE /api/auth/instagram/session/{username}` (path param)
- `GET /api/auth/status` returns `{users, has_session, gemini_key, maps_key}` (NOT `instagram`)
- All collection/job/results routes require `?user=` query param
- Media route: `/media/{username}/{collection}/{path:path}`
- CLI: `--user` option on collect/analyze; `_resolve_user()` auto-detects single session from auth/sessions/
- Frontend: navbar user selector (`#active-user-select`), Setup tab account management, 2FA Cancel button

## Metadata Merge Fix (IMPLEMENTED)
- `download_collection_media()` now loads existing metadata.json on re-collect and preserves
  `caption_analysis` + `google_maps_enrichment` fields indexed by `pk`

## What's NOT Done Yet
1. **Gemini video analysis** — when caption has no location, upload video to Gemini and analyze. See `memory-bank/Plans.md` for spec. Reference `3rdparty/gemini_video.ipynb` for Gemini video API usage.
2. **CSV output** — export enriched metadata to CSV

## Testing
- `tests/conftest.py` sets dummy env vars (`GEMINI_API_KEY`, `GOOGLE_PLACES_API`) at session scope to prevent import-time errors
- All tests use mocks (no live API calls in unit tests)
- Run: `poetry run pytest` — 63 tests, all passing

## Known Constraints
- `instagrapi` uses unofficial Instagram API — can break with Instagram changes
- `location_enricher.py` initializes `gmaps` client at module import time (not class-based)
- Port 8000 is occupied by a Docker proxy on this machine — always use `--port 8001`
- Do NOT force aspect-ratio + overflow:hidden on video elements — breaks inline playback in browser
