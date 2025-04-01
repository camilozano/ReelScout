# Technical Context: ReelScout

*(This document details the technologies, setup, constraints, and dependencies for the ReelScout project.)*

**Core Technologies:**

*   **Programming Language:** Python (Assumed, based on AI/ML focus and available libraries).
*   **AI Service:** Google Gemini API (Specifically models capable of video analysis).
*   **Instagram Interaction:** TBD (Likely `instagrapi` library, based on project files, but needs confirmation/implementation).

**Development Setup:**

*   **Environment:** Local development environment (macOS).
*   **Dependencies:**
    *   `google-generativeai`: For interacting with the Gemini API. (Needs installation)
    *   `instagrapi`: For interacting with Instagram. (Needs installation)
    *   Other potential dependencies for video handling, data manipulation (e.g., `requests`, `ffmpeg-python`, `pandas`).
*   **Version Control:** Git (Assumed, standard practice).
*   **Configuration:** API keys (Gemini, potentially Instagram credentials) managed via environment variables or a secure configuration method (e.g., `.env` file in `auth/`).

**Technical Constraints:**

*   **API Limits:** Rate limits and usage quotas for both Instagram and Gemini APIs.
*   **Authentication:** Handling Instagram login/session management securely and reliably. Challenge resolution might be necessary.
*   **Video Size/Format:** Limitations imposed by Gemini API regarding video size, length, and supported formats.
*   **Unofficial API Risks:** If using `instagrapi` or similar, be aware of potential instability due to Instagram changes.

**Tool Usage Patterns:**

*   **IDE:** VS Code.
*   **Package Management:** `Poetry` (using `pyproject.toml`).
*   **Notebooks:** Jupyter Notebook (`3rdparty/gemini_video.ipynb`) used for initial exploration/prototyping with Gemini video capabilities.

*(This document will be updated as specific libraries are chosen, versions are pinned, and the development environment evolves.)*
