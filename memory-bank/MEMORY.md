# ReelScout - Project Memory

## Overview
ReelScout collects saved Instagram collection items, downloads local media plus metadata, analyzes captions with Gemini to extract locations, enriches those locations with Google Maps, and exposes the workflow through both a CLI and a FastAPI web app.

## Current Source of Truth
For this branch, trust the code more than older memory-bank history:
*   CLI: `reel_scout_cli.py`
*   Backend: `src/api/app.py`
*   Pipelines: `src/pipeline.py`
*   Tests: `tests/`

The current implementation is **single-user**, even though some older docs and parts of the frontend still reflect a planned multi-user design.

## Key Files
*   `reel_scout_cli.py` — CLI entrypoint with `collect`, `analyze`, `serve`
*   `src/pipeline.py` — collect/analyze pipeline orchestration
*   `src/instagram_client.py` — Instagram session login and collection/media access
*   `src/downloader.py` — downloads media and writes `metadata.json`
*   `src/ai_analyzer.py` — Gemini caption analysis
*   `src/location_enricher.py` — Google Maps enrichment
*   `src/api/app.py` — FastAPI routes, background jobs, SSE
*   `src/api/models.py` — request models for API endpoints
*   `src/web/index.html` — frontend
*   `pyproject.toml` — PEP 621 metadata, `hatchling` build config
*   `uv.lock` — lockfile

## Tech Stack
*   Python `>=3.11,<4`
*   `uv` for dependency locking, syncing, and runtime commands
*   `hatchling` for building the package
*   `instagrapi`
*   `google-genai`
*   `googlemaps`
*   `click`
*   `fastapi`
*   `uvicorn[standard]`
*   `pydantic`
*   `python-dotenv`

## Packaging / Tooling
*   Poetry has been removed from the project.
*   The console script is still `reel-scout = reel_scout_cli:cli`.
*   Hatchling wheel builds require explicit inclusion of `reel_scout_cli.py`.
*   Standard commands:
    *   `uv sync --group dev`
    *   `uv run pytest tests/`
    *   `uv run reel-scout serve --port 8001`
    *   `uv build`

## Data and Configuration
*   Instagram session file: `auth/session.json`
*   API keys file: `auth/.env`
*   Downloads directory: `downloads/{collection}/`
*   Metadata file: `downloads/{collection}/metadata.json`

## Current CLI Surface
*   `reel-scout collect`
    *   options: `--session-file`, `--download-dir`, `--skip-download`
*   `reel-scout analyze`
    *   options: `--collection-name`, `--download-dir`
*   `reel-scout serve`
    *   options: `--host`, `--port`, `--reload`

There is currently no `--user` CLI option and no `migrate` command in this branch.

## Current Backend Surface
*   `GET /`
*   `GET /media/{collection}/{path:path}`
*   `GET /api/auth/status`
*   `POST /api/auth/keys`
*   `POST /api/auth/instagram/login`
*   `POST /api/auth/instagram/2fa`
*   `DELETE /api/auth/instagram/session`
*   `GET /api/collections/instagram`
*   `GET /api/collections/local`
*   `POST /api/jobs/collect`
*   `POST /api/jobs/analyze`
*   `GET /api/jobs/{id}/status`
*   `GET /api/jobs/{id}/stream`
*   `GET /api/results/{collection}`

## Data Flow
1.  `collect`
    *   log in with the session file
    *   fetch collections
    *   fetch collection media
    *   download media and write `metadata.json`
2.  `analyze`
    *   load `metadata.json`
    *   run Gemini caption analysis
    *   run Google Maps enrichment
    *   write updated `metadata.json`

## Metadata Shape
Each item in `metadata.json` can include:
```json
{
  "relative_path": "filename.mp4 | filename.jpg | pk/ | null",
  "caption": "...",
  "url": "https://www.instagram.com/p/{code}/",
  "pk": 12345,
  "media_type": 1,
  "product_type": "...",
  "caption_analysis": {
    "location_found": true,
    "locations": ["Place, City"],
    "error": null
  },
  "google_maps_enrichment": [
    {
      "original_name": "Place, City",
      "google_maps_data": {},
      "error": null
    }
  ]
}
```

## Known Mismatch
The frontend currently includes multi-user UI logic (`/api/auth/users`, `?user=` parameters, `/media/{username}/...`) that does not match the current backend implementation. Treat this as a known inconsistency, not as implemented behavior.

## Testing
*   Tests are mocked; no live API calls are required for unit tests.
*   Current verified result: `uv run pytest tests/` → 61 passing tests.

## Next Product Work
*   Gemini video analysis fallback
*   CSV export
*   Resolve single-user vs multi-user architecture mismatch between frontend and backend
