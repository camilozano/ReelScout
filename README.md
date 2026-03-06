# 🗺️ ReelScout

> Turn your saved Instagram Reels into a travel map.

ReelScout digs through your saved Instagram collections, uses **Google Gemini AI** to extract location mentions from captions, enriches them with real **Google Maps** data, and presents everything in a clean web UI — so you can finally remember what that hidden rooftop bar was called.

---

## ✨ Features

- 🔐 **Multi-account Instagram support** — link multiple accounts, each stored as a local session file
- 📥 **Smart collection downloader** — downloads Reels, photos, and carousels with full metadata
- 🧠 **AI caption analysis** — Gemini Flash scans captions for location mentions (restaurants, viewpoints, landmarks)
- 📍 **Google Maps enrichment** — each found location is matched to a real Maps entry with a direct link
- 🌊 **Live progress streaming** — real-time SSE updates in the browser as jobs run
- 📱 **Mobile-optimized UI** — two-row navbar, full-width controls, 44px tap targets, works great on iPhone
- 🔄 **Incremental re-collect** — re-running a collection preserves existing AI analysis data
- 💻 **CLI + Web UI** — use the `reel-scout` command or open the browser app

---

## 🖼️ How It Works

```
Instagram Collection
       ↓  collect
 downloads/{user}/{collection}/
   ├── reel.mp4
   ├── photo.jpg
   ├── {pk}/              ← carousel subfolder
   └── metadata.json
       ↓  analyze
 Phase 1 — Gemini AI reads each caption → extracts location names
 Phase 2 — Google Maps Places API → enriches with real place data
       ↓
 Results tab — media previews · captions · Maps links · status badges
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 + uv |
| Instagram | `instagrapi` 2.3 (unofficial API) |
| AI | Google Gemini Flash (`google-genai`) |
| Maps | Google Maps Places API (`googlemaps`) |
| Backend | FastAPI + Uvicorn |
| Frontend | Vanilla JS + Tailwind CSS (CDN) |
| CLI | Click |
| Validation | Pydantic v2 |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- A [Google Gemini API key](https://aistudio.google.com/)
- A [Google Maps Places API key](https://console.cloud.google.com/)
- An Instagram account with saved collections

### Install

```bash
git clone https://github.com/you/ReelScout.git
cd ReelScout
uv sync --group dev
```

### Configure

Create `auth/.env`:

```env
GEMINI_API_KEY=AIza...
GOOGLE_PLACES_API=AIza...
```

### Run the Web UI

```bash
uv run reel-scout serve --port 8001
```

Open [http://localhost:8001](http://localhost:8001) and follow the four tabs:

| Tab | What it does |
|---|---|
| ⚙️ **Setup** | Log in to Instagram · save API keys · manage accounts |
| 📥 **Collect** | Pick a saved collection and download all the media |
| 🧠 **Analyze** | Run AI caption analysis + Google Maps enrichment |
| 📊 **Results** | Browse locations, preview media, open Maps links |

### Or use the CLI

```bash
# Download a collection interactively
uv run reel-scout collect

# Run analysis on a downloaded collection
uv run reel-scout analyze --collection-name "My Collection"
```

### Build and install the CLI package

```bash
uv build
python3 -m pip install dist/reel_scout-0.1.0-py3-none-any.whl
reel-scout --help
```

---

## 📁 Project Structure

```
ReelScout/
├── reel_scout_cli.py        # CLI entrypoint (click)
├── src/
│   ├── pipeline.py          # Pipeline orchestration with progress callbacks
│   ├── instagram_client.py  # instagrapi login + collection/media fetching
│   ├── downloader.py        # Media download + metadata.json writer
│   ├── ai_analyzer.py       # Gemini AI caption analysis
│   ├── location_enricher.py # Google Maps Places enrichment
│   └── api/
│       ├── app.py           # FastAPI routes, SSE streaming, job runner
│       ├── jobs.py          # Thread-safe in-memory job store
│       └── models.py        # Pydantic request models
├── src/web/
│   └── index.html           # Single-file frontend (no build step)
├── auth/
│   ├── .env                 # API keys (git-ignored)
│   └── sessions/            # Per-user Instagram session files (git-ignored)
├── downloads/               # Downloaded media (git-ignored)
├── memory-bank/             # Project planning docs
└── tests/                   # pytest unit tests (63 passing)
```

---

## 📄 metadata.json Schema

Each downloaded collection produces a `metadata.json` alongside the media files:

```json
{
  "relative_path": "reel.mp4",
  "caption": "Best sunset spot in the city 📍 Mirador del Migdia, Barcelona",
  "url": "https://www.instagram.com/p/AbCdEfG/",
  "pk": 1234567890,
  "media_type": 2,
  "caption_analysis": {
    "location_found": true,
    "locations": ["Mirador del Migdia, Barcelona"]
  },
  "google_maps_enrichment": [{
    "original_name": "Mirador del Migdia, Barcelona",
    "google_maps_data": {
      "name": "Mirador del Migdia",
      "google_maps_uri": "https://maps.google.com/?cid=..."
    }
  }]
}
```

**Media types:** `1` = Photo · `2` = Video/Reel · `8` = Carousel

---

## 🤖 Built With AI

This project was built entirely through AI-assisted development — no manual coding:

- **v1** — [Cline](https://github.com/cline/cline) + Gemini 2.5 Pro *(initial prototype)*
- **v2+** — [Claude Code](https://claude.ai/code) with Claude Sonnet 4.6 *(current)*

The only human-written content is the high-level spec in [`memory-bank/Plans.md`](memory-bank/Plans.md).

---

## ⚠️ Disclaimer

Uses `instagrapi`, an unofficial Instagram API client. Use responsibly and at your own risk — Instagram may change their internals at any time. This tool is intended for personal use only.
