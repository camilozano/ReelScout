# Active Context: ReelScout

*(This document tracks the current focus, recent changes, next steps, active decisions, and current repo mismatches.)*

**Current Focus:** Implement Gemini video analysis without destabilizing the existing caption-analysis and enrichment flow.

**Current Repo State (06 Mar 2026):**
*   Tooling has been migrated from Poetry to `uv` for locking/sync/runtime commands and `hatchling` for builds.
*   The installable CLI currently exposes only `collect`, `analyze`, and `serve` from `reel_scout_cli.py`.
*   The backend in `src/api/app.py` is currently **single-user** and uses `auth/session.json` plus `downloads/{collection}/`.
*   The frontend in `src/web/index.html` is currently **ahead of the backend** and still expects multi-user endpoints such as `/api/auth/users`, `?user=...` query parameters, and `/media/{username}/{collection}/...`.
*   The tested backend/data pipeline path is the single-user CLI plus the pipeline modules.

**Recent Changes:**
*   **uv Toolchain Migration (06 Mar 2026):**
    *   Replaced Poetry-specific metadata in `pyproject.toml` with PEP 621 `[project]` metadata.
    *   Switched the build backend to `hatchling`.
    *   Replaced `poetry.lock` with `uv.lock`.
    *   Preserved the `reel-scout` console script via `[project.scripts]`.
*   **Wheel Packaging Fix (06 Mar 2026):**
    *   Added Hatchling `force-include` for `reel_scout_cli.py`.
    *   This was necessary because the first Hatchling build produced a wheel that contained the console-script metadata but omitted the referenced module.
*   **CI Migration and Trigger Update (06 Mar 2026):**
    *   GitHub Actions now use `uv sync`, `uv run pytest`, and `uv build`.
    *   Workflows were broadened to run on all branches and pull requests.
    *   The build workflow artifact name was changed to a slash-safe format after branch names like `codex/uv-migration` broke artifact upload.

**Verified Working:**
*   `uv lock`
*   `uv sync --group dev`
*   `uv run reel-scout --help`
*   `uv run reel-scout collect --help`
*   `uv run reel-scout analyze --help`
*   `uv run reel-scout serve --help`
*   `uv run pytest tests/` → 61 passing tests
*   `uv build` → wheel and sdist build successfully

**Current Decisions:**
*   Keep the direct dependency versions/ranges conservative during the tooling migration; do not mix package upgrades into unrelated work.
*   Treat the current codebase as single-user until the backend and frontend are reconciled.
*   Treat CLI + pipeline behavior as the most reliable source of truth because tests currently cover that path.

**Known Inconsistencies / Risks:**
*   The memory bank historically described a multi-user implementation as if it were complete, but the code in this branch does not currently match that description.
*   The frontend appears to target a more advanced multi-user API than the backend currently implements.
*   `src/ai_analyzer.py` currently uses `gemini-3-flash-preview`; older memory-bank entries mentioning `models/gemini-2.0-flash-exp` are stale.
*   `instagrapi` remains an unofficial dependency and can break with Instagram-side changes.

**Next Steps:**
1.  Decide whether to bring the backend up to the frontend’s multi-user assumptions or simplify the frontend back to the current single-user backend.
2.  Implement Gemini video analysis as the next product feature after the backend/frontend state is clarified.
3.  Keep memory-bank “current state” docs aligned to actual code, not prior plans.

**Useful Commands:**
*   `uv sync --group dev`
*   `uv run pytest tests/`
*   `uv run reel-scout serve --port 8001`
*   `uv build`
