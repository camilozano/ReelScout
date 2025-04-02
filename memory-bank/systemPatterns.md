# System Patterns: ReelScout

*(This document outlines the high-level architecture, key technical decisions, design patterns, and component relationships.)*

**Current Architecture:**

```mermaid
graph TD
    subgraph User_Interaction["User Interaction"]
        A["CLI (reel-scout)"]
    end

    subgraph Core_Modules["Core Modules"]
        B["Instagram Client (src/instagram_client.py)"]
        C["Downloader (src/downloader.py)"]
        D["AI Analyzer (src/ai_analyzer.py)"]
        LE["Location Enricher (src/location_enricher.py)"]
        E["Output Handler (TBD - currently handled in CLI)"]
    end

    subgraph Data["Data"]
        F["auth/session.json"]
        G["auth/.env"]
        H["downloads/{collection_name}/metadata.json"]
        I["downloads/{collection_name}/{video_files}"]
        J["Analysis Results (e.g., CSV, updated JSON)"]
    end

    subgraph External_Services["External Services"]
        K["Instagram (via instagrapi)"]
        L["Google Gemini API (via google-generativeai)"]
        GMaps["Google Maps API (via googlemaps)"]
    end

    A --> B
    A --> C
    A --> D
    A --> LE
    A --> E

    B -->|Reads| F
    B -->|Interacts| K
    B -->|Collection/Media Info| A

    C -->|Reads| H
    C -->|Writes| I
    C -->|Video Path/Metadata| A

    D -->|Reads| G
    D -->|Reads Caption| A
    D -->|"Reads Video (Future)"| I
    D -->|Interacts| L
    D -->|Analysis| A

    LE -->|Reads| G
    LE -->|Interacts| GMaps
    LE -->|Enrichment Data| A

    A -->|Updates| H
    E -->|Writes| J
```

**Key Technical Decisions:**

*   **Instagram Library:** `instagrapi` (Chosen, implemented in `src/instagram_client.py`).
*   **Google Maps Library:** `googlemaps` (Chosen, implemented in `src/location_enricher.py`).
*   **CLI Framework:** `click` (Chosen, implemented in `reel_scout_cli.py`).
*   **Dependency Management:** `Poetry` (Chosen).
*   **Path Handling:** `pathlib` (Chosen).
*   **Configuration:** Session via `auth/session.json`, API Keys (`GEMINI_API_KEY`, `GOOGLE_PLACES_API`) via `auth/.env` (using `python-dotenv`).
*   **Video Handling:** Videos are downloaded locally first (`src/downloader.py`).
    *   **Gemini Model (Text):** `models/gemini-2.0-flash-exp` (Updated 01 Apr 2025 from `models/gemini-1.5-pro-latest` per user request; originally fixed from `gemini-pro` 404 error).
    *   **Gemini Model (Video):** TBD (e.g., `gemini-pro-vision`, `gemini-1.5-flash`).
    *   **Programming Language:** Python 3.
*   **Data Flow:** Primarily direct function calls between modules orchestrated by the CLI (`reel_scout_cli.py`). Metadata (`metadata.json`) is read, updated with AI analysis results, then updated again with Google Maps enrichment data within the `analyze` command.

**Design Patterns:**

*   **Modular Design:** Separate modules for distinct concerns (Instagram client, downloader, AI analyzer).
*   **Configuration Management:** Loading sensitive data (API keys) from environment variables via `.env`.

**Component Relationships:**

*   `reel_scout_cli.py`: Orchestrates the workflow, handles user input, and calls other modules.
*   `src/instagram_client.py`: Handles authentication and interaction with the Instagram API via `instagrapi`. Fetches collection and media data.
*   `src/downloader.py`: Downloads media files and saves initial metadata to `metadata.json`.
*   `src/ai_analyzer.py`: Handles interaction with the Google Gemini API. Contains function for text analysis (`analyze_caption_for_location`) and planned video analysis.
*   `src/location_enricher.py`: Handles interaction with the Google Maps Places API via `googlemaps`. Contains function `enrich_location_data` to find place details based on a name.
*   `Output Handler` (TBD): Currently, the final output (updated `metadata.json`) is handled directly within the `analyze` command in `reel_scout_cli.py`. A separate handler might be created later for different output formats (e.g., CSV).

*(This document will be updated as the architecture evolves and further decisions are made.)*
