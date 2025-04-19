# Progress: ReelScout

*(This document tracks what works, what's left, current status, known issues, and the evolution of project decisions.)*

**Current Status:** Gemini text analysis and Google Maps location enrichment integrated into the `analyze` CLI command (02 Apr 2025). CLI for collection download works.

**What Works:**
*   Memory Bank structure established and populated.
*   Dependency management using Poetry (`pyproject.toml`), including `google-genai` and `python-dotenv`. **Updated (19 Apr 2025):** Migrated from `google-generativeai`.
*   Installable CLI (`reel-scout`) via Poetry script configuration, using `click`.
*   Instagram login using session file (`src/instagram_client.py` with `instagrapi`).
*   Fetching user's saved collections.
*   Fetching media items within a selected collection.
*   **Downloading Media (19 Apr 2025):** Handles videos (`media_type=2`), photos (`media_type=1`), and carousels (`media_type=8`).
    *   Downloads videos and photos directly into the collection directory.
    *   For carousels, creates a subdirectory named after the carousel's PK and downloads individual photo/video resources into that subdirectory.
    *   Saves metadata for all processed types (videos, photos, carousels) to `metadata.json`.
    *   `relative_path` in metadata stores the filename for videos/photos, and the relative subdirectory path (e.g., `{pk}/`) for carousels.
*   Option to skip media download and only collect metadata (`--skip-download` flag). Works for all types (videos, photos, carousels - creates carousel subdir even if skipping resource downloads).
*   **Downloader Idempotency (Updated 19 Apr 2025):**
    *   Checks if a video/photo file matching the media PK already exists before downloading.
    *   Checks if a carousel subdirectory exists and is non-empty before processing resources.
    *   Checks if individual carousel resource files exist before downloading them.
    *   Skips download if item/resource already exists, logs appropriately, and records the existing filename/subdir path in metadata.
    *   Unit tested (`tests/test_downloader.py`) for all media types and skip scenarios.
*   Basic Gemini text analysis (`src/ai_analyzer.py::analyze_caption_for_location`):
    *   Loads API key (`GEMINI_API_KEY`) from `auth/.env`.
    *   Uses `models/gemini-2.0-flash-exp` model (Updated 01 Apr 2025 from `models/gemini-1.5-pro-latest` per user request; originally fixed from `gemini-pro` 404 error).
    *   Prompts for specific location extraction, including geographical context (city, region, etc.).
    *   **Uses Gemini's native JSON mode** (`response_mime_type="application/json"`, `response_schema=LocationResponse`) for reliable structured output (`{"location_found": bool, "locations": Optional[List[str]]}`) (Refactored 01 Apr 2025).
    *   Uses `pydantic` (v2.10.1) for schema definition.
    *   Includes error handling for API calls and response processing (using `response.parsed` with fallback).
    *   **Unit Tested (01 Apr 2025):** Mocked unit tests (`tests/test_ai_analyzer.py`) cover various success and error scenarios.
*   Google Maps Location Enrichment (`src/location_enricher.py::enrich_location_data`):
    *   Loads API key (`GOOGLE_PLACES_API`) from `auth/.env`.
    *   Uses `googlemaps` library to query Places API (`find_place` to get `place_id`, then `place` to get details including Google Maps URI). **Updated (02 Apr 2025):** Now makes two calls to get `google_maps_uri`.
    *   Returns structured data (name, address, place_id, lat/lng, google_maps_uri).
    *   Includes error handling for API calls and responses.
    *   **Integrated (02 Apr 2025):** Called from `reel_scout_cli.py analyze` command after AI analysis finds locations. Updates `metadata.json` with `google_maps_enrichment` data.
    *   **Unit Tested (02 Apr 2025):** Mocked unit tests (`tests/test_location_enricher.py`) cover success, zero results, API errors/exceptions, invalid input, and the two-step API call process.

**What's Left to Build (High-Level):**
*   **Gemini Video Analysis:**
    *   Select appropriate Gemini model (e.g., `gemini-pro-vision`, `gemini-1.5-flash`).
    *   Implement video file upload/processing for Gemini API.
    *   Create `analyze_video_for_location` function in `src/ai_analyzer.py`.
    *   Integrate video analysis into the `analyze` command (e.g., run if caption analysis fails or if specifically requested).
    *   Add unit tests for video analysis function.
*   **Output/Storage:**
    *   Refine `metadata.json` structure if needed for video analysis results.
    *   *Optional:* Add a dedicated output command/option (e.g., to generate CSV from enriched `metadata.json`).
*   **Refinements:**
    *   More robust error handling for AI analysis and Google Maps enrichment (API limits, content filtering, etc.).
    *   Enhanced logging.
    *   *Optional:* Integration tests for AI analyzer and location enricher (hitting live APIs).
    *   Potentially handle non-video media types differently if needed later. **(Addressed 19 Apr 2025)**

**Known Issues:**
*   **FIXED (19 Apr 2025):** Downloader previously only handled video (`media_type=2`), ignoring photos and carousels. Now handles all three types.
*   **FIXED (01 Apr 2025):** Pytest failure in `test_collect_success_custom_paths` due to `click.Path` validation checks failing before patches were active. Fixed by creating the temporary file/directory directly in the test setup instead of patching `os` functions.
*   **FIXED (01 Apr 2025):** `ValueError` during relative path calculation in `src/downloader.py` due to comparing absolute download path with relative base directory path. Fixed by resolving the base path to absolute in `reel_scout_cli.py`.
*   **FIXED (01 Apr 2025):** Gemini API call failed with 404 error for `gemini-pro` and `gemini-1.0-pro` models. Fixed by using `genai.list_models()` to find an available model (`models/gemini-1.5-pro-latest`) and updating `src/ai_analyzer.py`.
*   **FIXED (02 Apr 2025):** `ValueError` in `src/location_enricher.py` due to requesting invalid 'url' field from Google Maps `find_place` API. Fixed by removing 'url' from the requested fields and updating tests.
*   Potential instability due to reliance on unofficial Instagram API (`instagrapi`).
*   Potential costs/rate limits associated with Google Maps Places API usage during enrichment.
*   Video analysis is not implemented (including tests).
*   Dependency constraint: `pydantic` pinned to `2.10.1` due to `instagrapi` requirement.

**Decision Log:**
*   **19 Apr 2025:** Modified `src/downloader.py` and `tests/test_downloader.py` to handle photos (`media_type=1`) and carousels (`media_type=8`) alongside videos (`media_type=2`). Carousels now download resources into a PK-named subdirectory. Updated Memory Bank files (`activeContext.md`, `progress.md`, `systemPatterns.md`).
*   **19 Apr 2025:** Migrated from `google-generativeai` to `google-genai` library due to deprecation. Updated dependencies (`pyproject.toml`), refactored AI analyzer (`src/ai_analyzer.py`) for new client/types/errors/response handling, updated unit tests (`tests/test_ai_analyzer.py`), and updated relevant Memory Bank files (`techContext.md`, `activeContext.md`, `progress.md`).
*   **02 Apr 2025:** Modified `src/downloader.py` to check for existing *video* files using `Path.glob(f"{media.pk}*")` before downloading to prevent duplicates. Updated summary output and added unit tests for this behavior. *(Superseded by 19 Apr 2025 update for all types)*.
*   **02 Apr 2025:** Modified `src/location_enricher.py` to use a two-step process: `find_place` to get `place_id`, then `place` to get details including the Google Maps URI ('url' field). Updated unit tests accordingly.
*   **02 Apr 2025:** Fixed `ValueError` in `src/location_enricher.py` by removing the invalid 'url' field request from the Google Maps `find_place` API call and updated corresponding unit tests.
*   **02 Apr 2025:** Added `googlemaps` library and implemented `src/location_enricher.py`. Integrated enrichment into the `analyze` CLI command to update `metadata.json` after AI analysis. Added unit tests for the enricher.
*   **01 Apr 2025:** Added mocked unit tests for `analyze_caption_for_location`. Updated function to use `model_dump()` instead of deprecated `dict()`.
*   **01 Apr 2025:** Refactored `analyze_caption_for_location` to use Gemini's native JSON mode with a Pydantic schema instead of relying on prompt engineering for JSON output, improving reliability. Added `pydantic` dependency.
*   **01 Apr 2025:** Implemented initial text analysis using `gemini-pro` and structured JSON output via prompting. Added `google-generativeai` and `python-dotenv` dependencies. Created `src/ai_analyzer.py`.
*   **01 Apr 2025:** Determined that patching `os.path.exists` and `os.access` was insufficient for `click.Path` validation in tests. Switched strategy to creating the necessary temporary file/directory using `tmp_path` fixture (`custom_session.touch()`, `custom_download.mkdir()`) to satisfy Click's checks directly.
*   **01 Apr 2025:** Decided to use `.resolve()` on the `download_dir` Path object in `reel_scout_cli.py` to ensure an absolute path is passed to the downloader function, fixing the `relative_to` error.
*   **01 Apr 2025:** Switched Gemini text model from `gemini-pro` to `models/gemini-1.5-pro-latest` after diagnosing 404 errors using `genai.list_models()`.
*   **01 Apr 2025:** Switched Gemini text model from `models/gemini-1.5-pro-latest` to `models/gemini-2.0-flash-exp` per user request.
*   *(Implicit)* Chose `instagrapi` for Instagram interaction.
*   *(Implicit)* Chose `click` for CLI framework.
*   *(Implicit)* Chose `pathlib` for path operations.

*(This file will track the project's journey from concept to functional prototype and beyond.)*
