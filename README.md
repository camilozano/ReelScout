# ReelScout 🗺️✨

ReelScout helps you rediscover the amazing places hidden in your saved Instagram Reels collections! 📌

Ever save tons of travel Reels but struggle to remember the specific restaurants, viewpoints, or hidden gems mentioned? ReelScout uses AI to automatically analyze your saved collections and extract location data, making trip planning or revisiting cool spots a breeze. 🌬️

## 🎯 Core Aim

This tool aims to:

1.  Securely connect to your Instagram account.
2.  Access your saved post collections.
3.  Download the Reels from a selected collection.
4.  Analyze video captions and/or video content using Google Gemini AI 🧠 to identify specific locations mentioned.
5.  Output a structured list (like a CSV) linking each Reel to the locations found within it.
6.  (Bonus) Find corresponding Google Maps URLs for the identified locations. 📍

## ⚙️ How it Works (The Plan)

1.  **Login:** Authenticate with Instagram using `instagrapi` and a session file.
2.  **Select:** Choose one of your saved Instagram collections.
3.  **Download:** Fetch and save the videos and their metadata (captions, URLs) locally.
4.  **Analyze:** Use Gemini AI to check captions and video content for location mentions.
5.  **Output:** Generate a data file (e.g., CSV) mapping Reels to locations.
6.  **Enhance:** (Optional) Add Google Maps links for discovered places.
7.  **Future UI:** Eventually, provide a simple interface to manage collections and view results. 🖥️

## ✅ Project Progress Checklist

Here's a snapshot of where the project stands:

*   [x] Project Concept Defined (`Plans.md`) 📝
*   [x] Initial Project Structure Setup
*   [x] Memory Bank Documentation Initialized 🧠
*   [ ] **Instagram Integration:**
    *   [x] Identify `instagrapi` as the library.
    *   [x] Define session file authentication (`auth/session.json`).
    *   [X] Implement login logic.
    *   [X] Implement collection listing and selection.
    *   [X] Implement post URL compilation.
*   [ ] **Downloader Module:**
    *   [x] Basic `downloader.py` structure exists.
    *   [X] Implement video downloading logic.
    *   [X] Implement metadata saving (JSON).
*   [ ] **Video Processing (AI Analysis):**
    *   [x] Identify Google Gemini API (Flash model) as the AI tool.
    *   [x] Locate API key (`auth/.env`).
    *   [ ] Provide Gemini video processing example (`3rdparty/gemini_video.ipynb`).
    *   [ ] Implement logic to analyze captions via Gemini.
    *   [ ] Implement logic to analyze video via Gemini if caption fails.
    *   [ ] Implement structured output generation for locations.
*   [ ] **Output Generation:**
    *   [ ] Implement CSV output generation (Post URL, Locations).
*   [ ] **Data Cleanup (Bonus):**
    *   [ ] Implement Google Maps URL fetching (via Gemini Search or Places API).
*   [ ] **CLI/TUI:**
    *   [x] Basic `reel_scout_cli.py` exists.
    *   [ ] Develop full CLI/TUI functionality.
*   [ ] **UI (Future):**
    *   [ ] Design and implement frontend interface.

## 🛠️ Tech Stack (Planned)

*   **Language:** Python 🐍
*   **Instagram:** `instagrapi`
*   **AI:** Google Gemini API
*   **Potential Libs:** `pandas`, `requests`, `python-dotenv`

---

*This README provides a high-level overview. For more detailed plans, see `Plans.md`.*
