#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd -P)"
PACKAGE_ROOT="$(cd "$ROOT/.." && pwd -P)"
LOG="$PACKAGE_ROOT/notes-atlas-launch.log"
PYTHON_BIN="$(command -v python3 || true)"

if [[ -z "$PYTHON_BIN" ]] && [[ -x /usr/bin/python3 ]]; then
  PYTHON_BIN="/usr/bin/python3"
fi

if [[ -z "$PYTHON_BIN" ]]; then
  echo "python3 not found" >&2
  exit 1
fi

if /usr/bin/curl -fsS http://127.0.0.1:8765/ >/dev/null 2>&1; then
  exit 0
fi

if pgrep -f "$ROOT/server.py --host 127.0.0.1 --port 8765" >/dev/null 2>&1; then
  exit 0
fi

cd "$ROOT"
nohup "$PYTHON_BIN" -u "$ROOT/server.py" --host 127.0.0.1 --port 8765 >>"$LOG" 2>&1 < /dev/null &
