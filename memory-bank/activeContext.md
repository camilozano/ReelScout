# Active Context: ReelScout

*(This document tracks the current focus, recent changes, next steps, active decisions, patterns, and learnings.)*

**Current Focus:** Fixing a bug in the video download path calculation.

**Recent Changes:**
*   **Bug Fix (01 Apr 2025):** Modified `reel_scout_cli.py` to resolve the `download_dir` path to an absolute path using `.resolve()` before passing it to `src/downloader.py`. This fixes an error where `pathlib.Path.relative_to()` failed because it was comparing an absolute download path with a relative base directory path.
*   **Implementation:** Developed the initial CLI (`reel_scout_cli.py`), Instagram client (`src/instagram_client.py`), and downloader logic (`src/downloader.py`) to fetch and download media from saved collections.
*   **Project Renaming:** Renamed project from "Instarecs" to "ReelScout" across documentation.

**Next Steps:**
1.  Test the `collect` command again to ensure the path resolution fix works.
2.  Continue implementing the core workflow:
    *   Integrate Google Gemini for video analysis.
    *   Implement video processing/upload suitable for Gemini.
    *   Implement Gemini API call for video analysis.
    *   Display analysis results via the CLI.
    *   Refine error handling and logging.

**Active Decisions/Considerations:**
*   Determining the specific Gemini model for video analysis.
*   Defining the exact format for video data required by Gemini.
*   How to handle potential Gemini API errors and costs.

**Emerging Patterns/Preferences:**
*   Using `pathlib` for path manipulation.
*   Using `click` for the command-line interface.
*   Using `instagrapi` for Instagram interaction.
*   Storing session data in `auth/session.json`.
*   Using Memory Bank (Markdown files in `memory-bank/`) for project documentation.

**Learnings/Insights:**
*   Absolute vs. relative path handling is crucial when using `pathlib.Path.relative_to()`. Ensure consistent path types (both absolute or both relative to the same base) are used.
*   The project structure includes separate modules for CLI, Instagram client, and downloader logic.

*(This file should be updated frequently as work progresses.)*
