# Technical Context: ReelScout

*(This document captures the current tooling, dependencies, setup, and technical constraints for the repo as it exists now.)*

## Core Technologies
*   **Python:** `>=3.11,<4`
*   **Dependency/runtime tool:** `uv`
*   **Build backend:** `hatchling`
*   **Instagram access:** `instagrapi`
*   **AI analysis:** Google Gemini via `google-genai`
*   **Location enrichment:** Google Maps Places API via `googlemaps`
*   **CLI:** `click`
*   **Backend:** `fastapi` + `uvicorn`
*   **Validation:** `pydantic`

## Packaging and Environment
*   Project metadata lives in `pyproject.toml` under PEP 621 `[project]`.
*   Lockfile is `uv.lock`.
*   The project remains installable as a CLI package through:
    *   `[project.scripts]`
    *   `reel-scout = "reel_scout_cli:cli"`
*   Because the CLI module lives at the repo root instead of under the `src` package, Hatchling must explicitly include `reel_scout_cli.py` in wheel builds.

## Current Commands
*   Install/sync: `uv sync --group dev`
*   Run tests: `uv run pytest tests/`
*   Run CLI: `uv run reel-scout ...`
*   Build artifacts: `uv build`

## Configuration
*   Gemini API key: `auth/.env` as `GEMINI_API_KEY`
*   Google Maps API key: `auth/.env` as `GOOGLE_PLACES_API`
*   Instagram session: `auth/session.json`

## Current Runtime Shape
*   CLI and backend are currently single-user.
*   Downloads are stored under `downloads/{collection}/`.
*   API job state is in-memory via `src/api/jobs.py`.
*   Background work runs in daemon threads because the key libraries are blocking/synchronous.

## CI
*   GitHub Actions test workflow uses `uv sync --group dev` and `uv run pytest tests/`.
*   GitHub Actions build workflow uses `uv build`.
*   Workflows currently run on all pushes and pull requests.

## Technical Constraints
*   `instagrapi` uses an unofficial Instagram API and may break externally.
*   Gemini and Google Maps usage is subject to API limits, quotas, and cost.
*   The frontend and backend are currently out of sync on the single-user vs multi-user model.
*   `src/location_enricher.py` initializes its Google Maps client at module import time.

## Notes
*   Current `AIAnalyzer` default model is `gemini-3-flash-preview`.
*   Current verified test count is 61 passing tests.
