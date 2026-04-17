# Notes Atlas

Version: `0.1`

Notes Atlas is a local macOS app bundle plus local website that turns Apple Notes into a searchable, filterable catalog without editing or moving anything inside the Notes app.

## Product Status

This is a usable `v0.1` alpha release.

Today it is good enough for:

- personal use on macOS
- first-time installation on another Mac
- local-only note cataloging and recategorization
- GitHub distribution as a public repo download

It is not yet a fully polished commercial product. Current limitations:

- macOS only
- Apple Notes required
- Safari is the supported browser target for the launcher workflow
- unsigned app bundles, so macOS Gatekeeper may require `Right-click > Open`
- no automated test suite yet
- not notarized or sandboxed

## What It Does

- reads Apple Notes through macOS Automation in a read-only way
- builds a local SQLite catalog with generated note titles, categories, subcategories, snippets, and dates
- lets users search, filter, and manually recategorize notes locally
- opens the selected note directly in Apple Notes
- keeps all note edits inside Apple Notes itself

## Privacy And Safety

- No external APIs are required.
- No API keys are required.
- No personal Notes content is shipped in this repository.
- The app binds to `127.0.0.1`, which is local-only on the user’s Mac.
- Notes Atlas does **not** create, edit, move, duplicate, or delete Apple Notes.
- The local catalog database is created on first run at:
  - `notes-catalog/data/notes_catalog.db`

## Quick Install

1. Download this repository as a ZIP from GitHub, or clone it locally.
2. Open the repository folder.
3. Open `Install Notes Atlas.app`.
4. If macOS blocks it, use `Right-click > Open`.
5. Choose an installation folder when prompted.
6. If Python 3 support is missing, let the installer trigger Apple’s Command Line Tools install.
7. Launch the installed `Notes Atlas.app`.
8. When macOS asks for permission to control `Notes` or `Safari`, click `Allow`.

## Included Apps

- `Install Notes Atlas.app`
  - guided installer for first-time setup
- `Notes Atlas.app`
  - launcher that starts the local server and opens the website in Safari

## Dependencies

Notes Atlas expects:

- macOS
- Apple Notes
- Safari
- `python3`
- `osascript`
- `curl`

Usually only `python3` may be missing on a fresh Mac. If needed:

```bash
xcode-select --install
```

No extra `pip install` step is required for the current release.

## First-Run Permissions

On first launch, macOS may prompt for Automation access so Notes Atlas, Python, or `osascript` can control:

- Notes
- Safari

Click `Allow`.

If permissions were denied before, reopen:

`System Settings > Privacy & Security > Automation`

and enable access for the relevant entries.

## Launch

The easiest path is:

- open `Notes Atlas.app`

Manual launch is also available:

```bash
cd "/path/to/NotesAtlas/notes-catalog"
./launch.sh
```

The site runs locally at:

- `http://127.0.0.1:8765`

## Repository Layout

- `Notes Atlas.app`
  - compiled launcher app bundle
- `Install Notes Atlas.app`
  - compiled installer app bundle
- `notes-catalog/`
  - backend, frontend, AppleScript sources, icon sources, and build helpers
- `VERSION.txt`
  - release marker

## Rebuild The App Bundles

If you change the AppleScript sources and want fresh app bundles:

```bash
cd "/path/to/NotesAtlas/notes-catalog"
./build_apps.sh
```

## Troubleshooting

- If the installer or launcher will not open, use `Right-click > Open`.
- If the website opens but cannot jump to Notes, re-enable Automation permissions.
- If Python is missing, run `xcode-select --install` and relaunch the installer.
- If the local catalog gets corrupted, delete `notes-catalog/data/notes_catalog.db` and sync again.

## License

This repository is licensed under the MIT License. See `LICENSE`.
