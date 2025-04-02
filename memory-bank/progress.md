# Progress: ReelScout

*(This document tracks what works, what's left, current status, known issues, and the evolution of project decisions.)*

**Current Status:** Gemini text analysis and Google Maps location enrichment integrated into the `analyze` CLI command (02 Apr 2025). CLI for collection download works.

**What Works:**
*   Memory Bank structure established and populated.
*   Dependency management using Poetry (`pyproject.toml`), including `google-generativeai` and `python-dotenv`.
*   Installable CLI (`reel-scout`) via Poetry script configuration, using `click`.
*   Instagram login using session file (`src/instagram_client.py` with `instagrapi`).
*   Fetching user's saved collections.
*   Fetching media items within a selected collection.
*   Downloading video media items to a specified directory (`src/downloader.py`).
*   Saving metadata (including relative path, caption, URL) for processed items to `metadata.json`.
*   Option to skip video download and only collect metadata (`--skip-download` flag).
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
    *   Potentially handle non-video media types differently if needed later.

**Known Issues:**
*   **FIXED (01 Apr 2025):** Pytest failure in `test_collect_success_custom_paths` due to `click.Path` validation checks failing before patches were active. Fixed by creating the temporary file/directory directly in the test setup instead of patching `os` functions.
*   **FIXED (01 Apr 2025):** `ValueError` during relative path calculation in `src/downloader.py` due to comparing absolute download path with relative base directory path. Fixed by resolving the base path to absolute in `reel_scout_cli.py`.
*   **FIXED (01 Apr 2025):** Gemini API call failed with 404 error for `gemini-pro` and `gemini-1.0-pro` models. Fixed by using `genai.list_models()` to find an available model (`models/gemini-1.5-pro-latest`) and updating `src/ai_analyzer.py`.
*   **FIXED (02 Apr 2025):** `ValueError` in `src/location_enricher.py` due to requesting invalid 'url' field from Google Maps `find_place` API. Fixed by removing 'url' from the requested fields and updating tests.
*   Potential instability due to reliance on unofficial Instagram API (`instagrapi`).
*   Potential costs/rate limits associated with Google Maps Places API usage during enrichment.
*   Video analysis is not implemented (including tests).
*   Dependency constraint: `pydantic` pinned to `2.10.1` due to `instagrapi` requirement.

**Decision Log:**
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
