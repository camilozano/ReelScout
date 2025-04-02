# Active Context: ReelScout

*(This document tracks the current focus, recent changes, next steps, active decisions, patterns, and learnings.)*

**Current Focus:** Implementing Gemini video analysis.

**Recent Changes:**
*   **AI Analyzer Unit Tests (01 Apr 2025):** Added mocked unit tests (`tests/test_ai_analyzer.py`) for `src/ai_analyzer.py::analyze_caption_for_location` using `pytest` and `pytest-mock`. Tests cover successful parsing (via `response.parsed` and fallback), empty input, API errors, and various JSON response handling scenarios (malformed JSON, incorrect structure, invalid types). Updated `analyze_caption_for_location` to use `model_dump()` instead of deprecated `dict()`.
*   **Gemini Structured Output (01 Apr 2025):** Refactored `src/ai_analyzer.py::analyze_caption_for_location` to use Gemini's native JSON mode. Added `pydantic` dependency (v2.10.1 due to `instagrapi` constraint). Defined a `LocationResponse` Pydantic model for the schema. Simplified the prompt and updated the `generate_content` call to use `generation_config` with `response_mime_type="application/json"` and the Pydantic schema. Updated response handling to use `response.parsed` with fallback to `json.loads(response.text)`.
*   **AI Prompt Update (01 Apr 2025):** Modified the prompt in `src/ai_analyzer.py::analyze_caption_for_location` to explicitly request geographical context (city, region, etc.) alongside specific locations.
*   **Gemini Model Change (01 Apr 2025):** Switched text analysis model in `src/ai_analyzer.py` from `models/gemini-1.5-pro-latest` to `models/gemini-2.0-flash-exp` per user request.
*   **Gemini Model Fix (01 Apr 2025):** Resolved 404 error during `reel-scout analyze`. The initial model (`gemini-pro`, then `gemini-1.0-pro`) was unavailable via the API endpoint being used by the `google-generativeai` library. Used `genai.list_models()` to identify available models and switched `src/ai_analyzer.py` to use `models/gemini-1.5-pro-latest`.
*   **Gemini Text Analysis (01 Apr 2025):** Added `google-generativeai` and `python-dotenv` dependencies via Poetry. Created `src/ai_analyzer.py` module. Implemented `analyze_caption_for_location` function using `gemini-pro` (later changed to `models/gemini-1.5-pro-latest`, then `models/gemini-2.0-flash-exp`) to extract specific locations from text captions, returning structured JSON via prompt engineering. Loads API key (`GEMINI_API_KEY`) from `auth/.env`.
*   **Poetry Migration (01 Apr 2025):** Migrated project from `requirements.txt` to Poetry for dependency management and packaging. Configured `pyproject.toml` to define dependencies, dev dependencies, and expose the CLI script (`reel-scout`). Updated GitHub Actions workflow to use Poetry.
*   **Test Fix (01 Apr 2025):** Resolved failure in `tests/test_reel_scout_cli.py::test_collect_success_custom_paths`. The issue stemmed from `click.Path` validation checks (`exists=True`, `readable=True`, `writable=True`, `dir_okay=True`) running before patches were active. The fix involved removing `os.path` patches and instead creating the required temporary file (`custom_session.touch()`) and directory (`custom_download.mkdir()`) using the `tmp_path` fixture before invoking the CLI command. This satisfies Click's validation using the actual filesystem state.
*   **Bug Fix (01 Apr 2025):** Modified `reel_scout_cli.py` to resolve the `download_dir` path to an absolute path using `.resolve()` before passing it to `src/downloader.py`. This fixes an error where `pathlib.Path.relative_to()` failed because it was comparing an absolute download path with a relative base directory path.
*   **Test Refactor (01 Apr 2025):** Initial attempt to update `tests/test_reel_scout_cli.py` (`test_collect_success_custom_paths`) involved mocking `pathlib.Path.exists`, which was insufficient due to Click's internal checks.
*   **Implementation:** Developed the initial CLI (`reel_scout_cli.py`), Instagram client (`src/instagram_client.py`), and downloader logic (`src/downloader.py`) to fetch and download media from saved collections.
*   **Project Renaming:** Renamed project from "Instarecs" to "ReelScout" across documentation.

**Next Steps:**
1.  Integrate `analyze_caption_for_location` into the main CLI workflow (e.g., add an `analyze` command or integrate into `collect`).
2.  Implement Gemini video analysis:
    *   Determine the appropriate Gemini model (e.g., `gemini-pro-vision`, `gemini-1.5-flash`).
    *   Implement video file upload/processing compatible with the chosen Gemini model (referencing `3rdparty/gemini_video.ipynb` and `3rdparty/python-genai-docs/`).
    *   Create a function `analyze_video_for_location` in `src/ai_analyzer.py`.
    *   Integrate video analysis into the workflow (e.g., call if caption analysis yields no results).
    *   Add unit tests for video analysis function.
3.  Implement logic to store/output the combined analysis results (e.g., update `metadata.json` or create a new output file/format like CSV).
4.  Refine error handling and logging for the AI analysis parts.

**Active Decisions/Considerations:**
*   Choosing the specific Gemini model for *video* analysis (balancing cost, capability, speed).
*   Defining the exact format for video data required by Gemini.
*   How to handle potential Gemini API errors and costs.

**Emerging Patterns/Preferences:**
*   Using `pathlib` for path manipulation.
*   Using `click` for the command-line interface.
*   Using `instagrapi` for Instagram interaction.
*   Using `google-generativeai` for Gemini interaction.
*   Using `pydantic` for data validation and schema definition (especially with Gemini JSON mode).
*   Using `python-dotenv` for loading environment variables.
*   Storing session data in `auth/session.json`.
*   Storing API keys in `auth/.env`.
*   Using Memory Bank (Markdown files in `memory-bank/`) for project documentation.

**Learnings/Insights:**
*   **Gemini Structured Output (01 Apr 2025):** Using Gemini's native JSON mode (`response_mime_type="application/json"` and `response_schema`) provides more reliable structured output than prompt engineering alone. The SDK's `response.parsed` feature (using Pydantic) simplifies accessing the structured data, though fallback parsing of `response.text` is still prudent.
*   **Dependency Conflicts (01 Apr 2025):** Poetry helps identify and resolve dependency conflicts. Sometimes specific versions must be pinned to satisfy requirements of multiple packages (e.g., `pydantic==2.10.1` needed for `instagrapi==2.1.3`).
*   **Gemini Model Availability (01 Apr 2025):** Specific Gemini model names (e.g., `gemini-pro`) might not be available depending on the API key, region, or the specific API endpoint the client library uses. Using `genai.list_models()` is crucial for diagnosing 404 errors and finding a working model identifier (e.g., `models/gemini-1.5-pro-latest`).
*   Absolute vs. relative path handling is crucial when using `pathlib.Path.relative_to()`. Ensure consistent path types (both absolute or both relative to the same base) are used.
*   The project structure includes separate modules for CLI (`reel_scout_cli.py`), Instagram client (`src/instagram_client.py`), downloader logic (`src/downloader.py`), and AI analysis (`src/ai_analyzer.py`).
*   Gemini API *can* be prompted to return structured JSON via text instructions, but parsing requires cleanup and error handling, making the native JSON mode preferable.

*(This file should be updated frequently as work progresses.)*
