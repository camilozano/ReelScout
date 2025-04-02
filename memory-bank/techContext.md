# Technical Context: ReelScout

*(This document details the technologies, setup, constraints, and dependencies for the ReelScout project.)*

**Core Technologies:**

*   **Programming Language:** Python 3.
*   **AI Service:** Google Gemini API (using `google-generativeai` library).
    *   Text Analysis: `models/gemini-2.0-flash-exp` model (Updated 01 Apr 2025 from `models/gemini-1.5-pro-latest` per user request; originally fixed from `gemini-pro` 404 error).
    *   Video Analysis: TBD (e.g., `gemini-pro-vision`, `gemini-1.5-flash`).
*   **Instagram Interaction:** `instagrapi` library.
*   **CLI Framework:** `click`.

**Development Setup:**

*   **Environment:** Local development environment (macOS).
*   **Dependencies (Managed by Poetry in `pyproject.toml`):**
    *   `google-generativeai`: For interacting with the Gemini API.
    *   `instagrapi`: For interacting with Instagram.
    *   `click`: For building the CLI.
    *   `python-dotenv`: For loading environment variables from `.env`.
    *   `pathlib`: (Built-in) For path manipulation.
    *   *Dev Dependencies:* `pytest`, `pytest-mock`, etc. (See `pyproject.toml`).
*   **Version Control:** Git.
*   **Configuration:**
    *   Gemini API Key: Stored in `auth/.env` under the `GEMINI_API_KEY` variable, loaded via `python-dotenv`.
    *   Instagram Session: Stored in `auth/session.json`, loaded by `instagrapi`.

**Technical Constraints:**

*   **API Limits:** Rate limits, usage quotas, and potential costs associated with Google Gemini API calls. Content filtering by Gemini might also affect results.
*   **Authentication:** Handling Instagram login/session management securely and reliably via `instagrapi`. Challenge resolution might be necessary. Session validity can expire.
*   **Video Size/Format:** Limitations imposed by the chosen Gemini video model regarding video size, length, and supported formats. File API limitations (size, duration) if used for uploads.
*   **Unofficial API Risks:** `instagrapi` relies on an unofficial Instagram API, making it susceptible to breaking changes by Instagram.

**Tool Usage Patterns:**

*   **IDE:** VS Code.
*   **Package Management:** `Poetry` (using `pyproject.toml`).
*   **Notebooks:** Jupyter Notebook (`3rdparty/gemini_video.ipynb`) used for initial exploration/prototyping with Gemini video capabilities.

*(This document will be updated as specific libraries are chosen, versions are pinned, and the development environment evolves.)*
