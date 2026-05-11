# Notes Atlas

Version: `0.2`

Notes Atlas is a local macOS app that turns Apple Notes into a searchable, categorized knowledge atlas while keeping the actual note editing experience inside Apple Notes.

It runs a private local website on your Mac, reads Apple Notes through macOS Automation, builds a local SQLite catalog, and lets you jump from the catalog or mind map back into the original Apple Note.

## Product Status

This is a usable `v0.2` alpha release for macOS.

It is ready for:

- local personal use with Apple Notes
- first-time installation from this repository
- searching and filtering a large Apple Notes library
- local category and subcategory refinement
- opening notes directly in Apple Notes
- generating an interactive local mind map from the catalog

Current limitations:

- macOS only
- Apple Notes required
- Safari is the supported browser target for the launcher workflow
- app bundles are unsigned and not notarized, so macOS may require `Right-click > Open`
- no formal automated test suite yet
- no cloud sync, multi-user mode, or remote access

## What It Does

- Reads Apple Notes in a read-only way through AppleScript.
- Builds a local SQLite catalog of notes, generated titles, snippets, categories, subcategories, and dates.
- Lets you search and filter notes locally.
- Lets you create categories and move notes between categories without changing the notes themselves.
- Opens selected notes directly in Apple Notes.
- Generates an interactive dark-background mind map from local catalog data.

## Mind Maps

The `Generate Mind Map` button creates a local interactive graph in a new Safari tab.

The mind map uses:

- category nodes
- subcategory nodes
- note nodes
- recurring concept/keyword hub nodes extracted from cached titles, snippets, and searchable text

The graph is rendered locally in the browser with a physics-like layout. You can hover nodes to highlight nearby connections, search and filter the graph, toggle labels, pause/resume motion, fit the graph to the screen, and click note nodes to open the original Apple Note.

## Privacy And Safety

- No external APIs are required.
- No API keys are required.
- No personal Apple Notes content is shipped in this repository.
- The local server binds to `127.0.0.1`, which is local-only on your Mac.
- Notes Atlas does **not** create, edit, move, duplicate, or delete Apple Notes.
- Manual category changes are stored only in the local Notes Atlas database.
- The local catalog database is created on first run at:

```text
notes-catalog/data/notes_catalog.db
```

## Quick Install

1. Download this repository as a ZIP from GitHub, or clone it locally.
2. Open the downloaded `NotesAtlas` folder.
3. Open `Install Notes Atlas.app`.
4. If macOS blocks the app, use `Right-click > Open`.
5. Choose where Notes Atlas should be installed.
6. If Python 3 support is missing, let the installer trigger Apple's Command Line Tools installer.
7. Open the installed `Notes Atlas.app`.
8. When macOS asks for permission to control `Notes` or `Safari`, click `Allow`.

## Launch

The normal launch path is:

- Open `Notes Atlas.app`

The launcher starts the local server and opens:

```text
http://127.0.0.1:8765
```

Manual launch is also available:

```bash
cd "/path/to/NotesAtlas/notes-catalog"
./launch.sh
```

## Included Apps

- `Install Notes Atlas.app`
  - guided installer for first-time setup
- `Notes Atlas.app`
  - launcher that starts the local website and opens it in Safari

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

No extra `pip install` step is required for this release.

## First-Run Permissions

On first launch, macOS may prompt for Automation access so Notes Atlas, Python, or `osascript` can control:

- Notes
- Safari

Click `Allow`.

If permissions were denied before, reopen:

```text
System Settings > Privacy & Security > Automation
```

Enable access for the relevant Notes Atlas, Python, or `osascript` entries.

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
- If the catalog opens but cannot jump to a note, re-enable Automation permissions.
- If Python is missing, run `xcode-select --install` and relaunch the installer.
- If the local catalog gets corrupted, quit Notes Atlas, delete `notes-catalog/data/notes_catalog.db`, and sync again.
- If the mind map is slow on a very large library, use graph search/type filters or pause the layout after it settles.

## License

This repository is licensed under the MIT License. See `LICENSE`.
