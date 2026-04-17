#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd -P)"
PACKAGE_ROOT="$(cd "$ROOT/.." && pwd -P)"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}

trap cleanup EXIT

python3 "$ROOT/build_icon.py"
/usr/bin/iconutil -c icns "$ROOT/NotesAtlas.iconset" -o "$ROOT/NotesAtlas.icns"

rm -rf "$PACKAGE_ROOT/Notes Atlas.app" "$PACKAGE_ROOT/Install Notes Atlas.app"

osacompile -o "$TMP_DIR/Notes Atlas.app" "$ROOT/Notes Atlas Launcher.applescript"
cp "$ROOT/NotesAtlas.icns" "$TMP_DIR/Notes Atlas.app/Contents/Resources/applet.icns"
touch "$TMP_DIR/Notes Atlas.app"

osacompile -o "$TMP_DIR/Install Notes Atlas.app" "$ROOT/Install Notes Atlas.applescript"
cp "$ROOT/NotesAtlas.icns" "$TMP_DIR/Install Notes Atlas.app/Contents/Resources/applet.icns"
touch "$TMP_DIR/Install Notes Atlas.app"

/usr/bin/ditto "$TMP_DIR/Notes Atlas.app" "$PACKAGE_ROOT/Notes Atlas.app"
/usr/bin/ditto "$TMP_DIR/Install Notes Atlas.app" "$PACKAGE_ROOT/Install Notes Atlas.app"

echo "Rebuilt Notes Atlas.app and Install Notes Atlas.app"
