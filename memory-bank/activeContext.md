# Active Context: ReelScout

*(This document tracks the current focus, recent changes, next steps, active decisions, patterns, and learnings.)*

**Current Focus:** Renaming project from "Instarecs" to "ReelScout" across all documentation.

**Recent Changes:**
*   Updated `README.md` with the new project name "ReelScout".
*   Updated `memory-bank/projectbrief.md` with the new project name.
*   Updated `memory-bank/productContext.md` with the new project name and refined problem/solution statements based on README.
*   Updated `memory-bank/systemPatterns.md` with the new project name.
*   Updated `memory-bank/techContext.md` with the new project name.
*   Updated `memory-bank/activeContext.md` (this file) with the new project name and current focus.
*   Updated `memory-bank/progress.md` with the new project name.

**Next Steps:**
1.  Begin implementing the core workflow as outlined in `README.md`:
    *   Set up Python environment and install dependencies (`google-generativeai`, `instagrapi`).
    *   Implement Instagram authentication and Reel fetching using `instagrapi`.
    *   Implement video processing/upload for Gemini.
    *   Implement Gemini API call for video analysis.
    *   Display results.

**Active Decisions/Considerations:**
*   Confirming the use of `instagrapi` for Instagram interaction.
*   Determining the specific Gemini model for video analysis.
*   Defining the exact format for video data required by Gemini.
*   Establishing the structure for the main Python script/application.

**Emerging Patterns/Preferences:**
*   Using Markdown for documentation (Memory Bank).
*   Storing credentials/API keys in `auth/.env`.

**Learnings/Insights:**
*   Project involves integrating two distinct external services (Instagram, Gemini) with potentially complex authentication and data handling requirements.
*   The name "ReelScout" was chosen to better reflect the project's goal.

*(This file should be updated frequently as work progresses.)*
