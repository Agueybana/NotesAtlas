from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from catalog import CatalogStore


BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"


def json_response(handler: SimpleHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json(handler: SimpleHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length <= 0:
        return {}
    data = handler.rfile.read(length)
    return json.loads(data.decode("utf-8"))


def find_available_port(host: str, preferred_port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, preferred_port))
            return preferred_port
        except OSError:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])


def build_handler(store: CatalogStore):
    class CatalogHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(WEB_DIR), **kwargs)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def end_headers(self) -> None:  # noqa: N802
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            super().end_headers()

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/state":
                query = parse_qs(parsed.query)
                payload = store.query_state(
                    search=query.get("search", [""])[0],
                    category=query.get("category", [""])[0],
                    subcategory=query.get("subcategory", [""])[0],
                    page=int(query.get("page", ["1"])[0] or 1),
                    page_size=int(query.get("page_size", ["120"])[0] or 120),
                )
                json_response(self, payload)
                return
            if parsed.path == "/api/status":
                json_response(self, store.get_sync_status())
                return
            if parsed.path == "/api/mind-map-meta":
                json_response(self, store.mind_map_meta())
                return
            if parsed.path == "/api/mind-map":
                json_response(self, store.build_mind_map())
                return
            if parsed.path == "/" or parsed.path == "":
                self.path = "/index.html"
            return super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/api/sync":
                    started = store.start_sync()
                    status = store.get_sync_status()
                    json_response(self, {"started": started, "sync_status": status})
                    return
                if parsed.path == "/api/open":
                    payload = read_json(self)
                    store.open_note(payload.get("note_id", ""))
                    json_response(self, {"ok": True})
                    return
                if parsed.path == "/api/suggest-category":
                    payload = read_json(self)
                    suggestion_payload = store.suggest_categories(payload.get("note_id", ""))
                    json_response(self, suggestion_payload)
                    return
                if parsed.path == "/api/categories":
                    payload = read_json(self)
                    store.create_category(payload.get("category", ""), payload.get("subcategory", ""))
                    json_response(self, {"ok": True})
                    return
                if parsed.path == "/api/assign":
                    payload = read_json(self)
                    store.move_note(
                        payload.get("note_id", ""),
                        payload.get("category", ""),
                        payload.get("subcategory", ""),
                    )
                    json_response(self, {"ok": True})
                    return
            except Exception as exc:  # noqa: BLE001
                json_response(self, {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return

            json_response(self, {"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    return CatalogHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="Local Apple Notes catalog website")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--sync-only", action="store_true")
    parser.add_argument("--recategorize-uncategorized", action="store_true")
    args = parser.parse_args()

    store = CatalogStore(BASE_DIR)
    if args.recategorize_uncategorized:
        result = store.recategorize_uncategorized_blocking()
        print(json.dumps(result, indent=2))
        return 0

    if args.sync_only:
        store.sync_blocking()
        status = store.get_sync_status()
        print(json.dumps(status, indent=2))
        return 0

    port = find_available_port(args.host, args.port)
    handler_class = build_handler(store)
    httpd = ThreadingHTTPServer((args.host, port), handler_class)
    url = f"http://{args.host}:{port}"

    if store.count_active_notes() == 0:
        store.start_sync()

    if args.open_browser:
        threading.Timer(0.75, lambda: webbrowser.open(url)).start()

    print(f"Notes catalog running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
