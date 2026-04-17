# Notes Atlas Developer Notes

This folder contains the local backend, frontend, launcher scripts, AppleScript sources, and icon/build assets for Notes Atlas.

## Main Files

- `catalog.py`
  - Apple Notes sync, classification, local SQLite catalog, and reassignment logic
- `server.py`
  - local HTTP server and API endpoints
- `web/`
  - frontend HTML, CSS, and JavaScript
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

## Data Directory

- `data/`
  - created or reused at runtime for the local catalog database

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

## Rebuilding App Bundles

```bash
cd "/path/to/NotesAtlas/notes-catalog"
./build_apps.sh
```

That script:

- regenerates the icon assets
- rebuilds `../Notes Atlas.app`
- rebuilds `../Install Notes Atlas.app`

## Packaging Notes

- The app bundle logic is relative-path based and does not depend on the original author’s machine paths.
- The launcher and installer are unsigned AppleScript app bundles.
- The app is local-only and binds to `127.0.0.1`.

## Publish Hygiene

Do not commit:

- `data/notes_catalog.db`
- `data/notes_catalog.db-wal`
- `data/notes_catalog.db-shm`
- `notes-atlas-launch.log`
- `__pycache__/`
- `.DS_Store`
