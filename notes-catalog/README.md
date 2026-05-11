# Notes Atlas Developer Notes

This folder contains the local backend, frontend, launcher scripts, AppleScript sources, and icon/build assets for Notes Atlas.

## Main Files

- `catalog.py`
  - Apple Notes sync, classification, mind-map graph generation, local SQLite catalog, and reassignment logic
- `server.py`
  - local HTTP server and API endpoints
- `web/`
  - frontend HTML, CSS, and JavaScript
- `web/mind-map.html`
  - dark interactive mind-map canvas page
- `web/mind-map.js`
  - graph rendering, search/filtering, physics-like animation, and note-opening behavior
- `launch.sh`
  - direct development launch entrypoint
- `launch_background.sh`
  - background bootstrap used by the launcher app bundle
- `Notes Atlas Launcher.applescript`
  - source for `../Notes Atlas.app`
- `Install Notes Atlas.applescript`
  - source for `../Install Notes Atlas.app`
- `build_icon.py`
  - generates the iconset assets
- `build_apps.sh`
  - rebuilds both app bundles from source

## Runtime Data

Runtime data lives under:

```text
data/
```

The public repo intentionally does **not** include a live `notes_catalog.db`.

## Local Development

```bash
cd "/path/to/NotesAtlas/notes-catalog"
./launch.sh
```

Or:

```bash
cd "/path/to/NotesAtlas/notes-catalog"
python3 server.py --host 127.0.0.1 --port 8765 --open-browser
```

## Main API Endpoints

- `GET /api/state`
  - catalog state, filters, notes, categories, counts, and sync status
- `GET /api/status`
  - sync status
- `GET /api/mind-map-meta`
  - lightweight mind-map summary for the dashboard button
- `GET /api/mind-map`
  - full local graph payload for the mind-map canvas
- `POST /api/sync`
  - starts a local Apple Notes sync
- `POST /api/open`
  - opens a note in Apple Notes
- `POST /api/categories`
  - creates a local category/subcategory
- `POST /api/assign`
  - stores a local category override
- `POST /api/suggest-category`
  - suggests categories for an uncategorized note

## Rebuilding App Bundles

```bash
cd "/path/to/NotesAtlas/notes-catalog"
./build_apps.sh
```

That script:

- regenerates icon assets
- rebuilds `../Notes Atlas.app`
- rebuilds `../Install Notes Atlas.app`

## Packaging Notes

- The app bundle logic is relative-path based and does not depend on a specific developer machine path.
- The launcher and installer are unsigned AppleScript app bundles.
- The app is local-only and binds to `127.0.0.1`.
- Mind-map graph data is generated from the local SQLite catalog, not from a remote service.

## Publish Hygiene

Do not commit:

- `data/notes_catalog.db`
- `data/notes_catalog.db-wal`
- `data/notes_catalog.db-shm`
- `notes-atlas-launch.log`
- `__pycache__/`
- `.DS_Store`
