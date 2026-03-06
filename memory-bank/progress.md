# Progress: ReelScout

*(This document tracks what currently works, what is incomplete, and the most relevant decisions already made.)*

**Current Status (06 Mar 2026):** The repo has a working single-user CLI pipeline for collecting Instagram collection media, analyzing captions with Gemini, enriching locations with Google Maps, and serving a FastAPI UI. The Python toolchain has been migrated to `uv` + `hatchling`.

## What Works
*   `uv`-based developer workflow: `uv lock`, `uv sync --group dev`, `uv run ...`, `uv build`.
*   Installable CLI package with `reel-scout` console script.
*   Instagram login from `auth/session.json` via `instagrapi`.
*   Fetching saved collections and collection media.
*   Downloading videos (`media_type=2`), photos (`media_type=1`), and carousels (`media_type=8`).
*   Metadata capture to `downloads/{collection}/metadata.json`.
*   `--skip-download` flag on `collect`.
*   Caption analysis via Gemini JSON output in `src/ai_analyzer.py`.
*   Google Maps enrichment in `src/location_enricher.py`.
*   FastAPI app with:
    *   auth endpoints
    *   collection listing endpoints
    *   background collect/analyze jobs
    *   SSE job streaming
    *   results endpoint
    *   media serving route
*   Test suite passes: 61 tests.

## Verified in This Migration
*   Replaced Poetry metadata with PEP 621 project metadata in `pyproject.toml`.
*   Switched build backend from `poetry-core` to `hatchling`.
*   Replaced `poetry.lock` with `uv.lock`.
*   Updated GitHub Actions to use `uv`.
*   Fixed wheel packaging so `reel_scout_cli.py` is included in built wheels.
*   Fixed build artifact naming for branch builds so branch names containing `/` do not break upload-artifact.

## What Is Not Done
*   Gemini video analysis fallback when caption analysis finds no location.
*   CSV export of enriched metadata.
*   Reconciliation of frontend multi-user assumptions with the current single-user backend.

## Known Issues / Gaps
*   The frontend currently expects multi-user routes and `?user=` parameters that the backend does not implement in this branch.
*   Older memory-bank history previously described multi-user support as implemented; that is not accurate for the current code.
*   The backend and CLI currently use `auth/session.json`, not per-user session files.
*   The CLI currently does not expose `migrate` or `--user`.
*   `instagrapi` remains a long-term fragility point because it relies on Instagram’s unofficial API behavior.

## Decision Log
*   **06 Mar 2026:** Migrated the repo from Poetry to `uv` + `hatchling`.
*   **06 Mar 2026:** Kept the project installable as a CLI package through `[project.scripts]`.
*   **06 Mar 2026:** Added Hatchling `force-include` for `reel_scout_cli.py` after verifying the first built wheel was incomplete.
*   **06 Mar 2026:** Updated CI to run on all branches and pull requests.
*   **06 Mar 2026:** Fixed release workflow artifact naming to avoid invalid `/` characters from branch names.
*   **19 Apr 2025:** Migrated Gemini integration from `google-generativeai` to `google-genai`.
*   **19 Apr 2025:** Expanded downloader support to photos and carousels in addition to videos.
*   **02 Apr 2025:** Added Google Maps enrichment and integrated it into the analyze flow.
*   **01 Apr 2025:** Added structured Gemini caption analysis and the initial CLI/download pipeline.
