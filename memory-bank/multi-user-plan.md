# Multi-User Plan (unimplemented — saved for resuming)

Plan file also at: `/home/camilozano/.claude/plans/flickering-kindling-flurry.md`

## Summary of what needs to be built

### 1. Fix metadata merge in `src/downloader.py`
Re-running `collect` currently overwrites `caption_analysis` and `google_maps_enrichment` in `metadata.json`. Fix: load existing metadata.json at start of `download_collection_media()`, index by `pk`, merge analysis fields back in after building the new list before saving.

### 2. Backend: multi-user (`src/api/app.py` + `src/api/models.py`)
- Sessions: `auth/sessions/{username}.json` (was `auth/session.json`)
- Downloads: `downloads/{username}/{collection}/` (was `downloads/{collection}/`)
- Replace `_insta_client` (single) with `_insta_clients: Dict[str, InstagramClient]` per-user cache
- Add `_session_file(username)` helper
- Auto-migration on startup via `@app.on_event("startup")`: load old session, call `account_info()` to get username, move session + downloads to new structure
- New endpoint: `GET /api/auth/users` → `[{username, has_session}]`
- Updated: `GET /api/auth/status` returns `users: list[str]`, `has_session: bool`
- Updated: login/2fa endpoints save to `_session_file(username)`
- Updated: `DELETE /api/auth/instagram/session/{username}` (was parameterless)
- All collection/job/results/media endpoints gain `?user=` query param or `username` in body
- Media route: `/media/{username}/{collection}/{path:path}`
- Add `username: str` to `CollectJobRequest` and `AnalyzeJobRequest` in models.py

### 3. CLI changes (`reel_scout_cli.py`)
- Add `_resolve_user(user)` helper: auto-selects single session, errors on multiple without `--user`
- Add `--user` option to `collect` and `analyze` commands
- Add `migrate` CLI command (manual fallback if auto-migration fails)

### 4. Frontend (`src/web/index.html`)
- Global state: `let currentUser = null; let availableUsers = [];`
- Compact `<select id="active-user-select">` in navbar (right side, `ml-auto`)
- `refreshUserSelector()` → `GET /api/auth/users` → populates select, auto-selects first user
- `onUserChange(username)` → sets `currentUser`, reloads all dropdowns
- Setup tab: replace single login card with:
  - "Existing Accounts" panel: list users with Remove button + "+ Add Account" toggle button
  - "Add Account" form (hidden by default): same login flow + **Cancel** button
  - 2FA form gains **Cancel** button (clears `pendingTwofaToken`, hides 2FA, shows login)
- All fetch calls updated to pass `?user=${currentUser}` or `username: currentUser` in body
- Guard: if `currentUser` is null when Start Collect/Analyze clicked, show alert

### 5. 2FA status
The existing 2FA backend logic is CORRECT — calling `cl.login(username, password, verification_code=code)` on the same client object works in instagrapi. Only UI fix needed: add Cancel button.

## Implementation order
1. `src/downloader.py` — metadata merge fix + update tests
2. `src/api/models.py` — add username fields
3. `src/api/app.py` — full multi-user rewrite + migration
4. `reel_scout_cli.py` — --user option + migrate command
5. `src/web/index.html` — user selector + setup tab + API call updates

## Current data to migrate
- `auth/session.json` → `auth/sessions/{camilo_username}.json`
- `downloads/All posts/` → `downloads/{camilo_username}/All posts/`
