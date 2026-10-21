"""Loopback-only, read-only HTTP application by Jason Stys; not an Internet server.

Classes/functions: WorkbenchServer, Handler, make_server. Variables: CSP, ASSET_TYPES, DOWNLOAD_NAMES.
No upload, remote fetch, account, shell, or arbitrary file APIs. See docs/CODE_INDEX.md.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from dtnlab.engine import CHOICES, Settings, build_run, catalog
from dtnlab.reports import export_report

CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; font-src 'self'; base-uri 'none'; frame-ancestors 'none'; "
    "form-action 'none'; object-src 'none'"
)
ASSET_TYPES = {
    ".html": "text/html",
    ".js": "text/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}
DOWNLOAD_NAMES = {
    "input": "mission-network-input.json",
    "json": "mission-network-evidence.json",
    "csv": "mission-network-queues.csv",
    "html": "mission-network-evidence.html",
}


class WorkbenchServer(ThreadingHTTPServer):
    """Threaded server bound only to IPv4 loopback; assets is a dedicated build directory."""

    daemon_threads = True
    assets: Path


class Handler(BaseHTTPRequestHandler):
    """Dispatch allowlisted GET routes with bounded queries and same-origin enforcement."""

    server: WorkbenchServer
    server_version = "MissionNetworkLab"
    sys_version = ""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress URL logs; public data only, but no browsing-history log is needed."""

    def reply(
        self, status: int, body: bytes, content_type: str, filename: str | None = None
    ) -> None:
        """Set restrictive headers on successes and failures; never echo unsafe request text."""
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        try:
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
        except ConnectionError:
            # An intentionally canceled browser request has no peer to receive a second response.
            return

    def do_GET(self) -> None:
        """Serve reviewed scenarios and built assets; reject DNS rebinding and cross-origin use."""
        expected_host = f"127.0.0.1:{self.server.server_port}"
        if (
            self.headers.get_all("Host") != [expected_host]
            or self.headers.get("Origin") not in (None, f"http://{expected_host}")
            or self.headers.get("Sec-Fetch-Site") == "cross-site"
        ):
            self.reply(403, b"Forbidden origin", "text/plain")
            return
        if len(self.path) > 1024:
            self.reply(414, b"Request too long", "text/plain")
            return
        try:
            self.route()
        except ValueError:
            self.reply(400, b"Invalid experiment or format", "text/plain")
        except (OSError, RuntimeError):
            self.reply(500, b"Local resource unavailable", "text/plain")

    def route(self) -> None:
        """Resolve finite API options or exact static names; never expose source/hidden files."""
        url = urlsplit(self.path)
        query = parse_qs(url.query, keep_blank_values=True, max_num_fields=8)
        if url.path == "/api/health" and not query:
            self.reply(200, b'{"status":"ok","mode":"local-educational"}', "application/json")
        elif url.path == "/api/catalog" and not query:
            self.reply(200, json.dumps(catalog()).encode(), "application/json")
        elif url.path in ("/api/run", "/api/report"):
            if set(query) - {"scenario", *CHOICES, "format"} or any(
                len(v) != 1 for v in query.values()
            ):
                raise ValueError("Invalid query")
            options = {key: values[0] for key, values in query.items() if key != "format"}
            parsed: dict[str, Any] = {}
            for key, value in options.items():
                parsed[key] = value if key == "scenario" else int(value)
            settings = Settings(**parsed)
            format_name = query.get("format", ["json"])[0]
            if url.path == "/api/run" and "format" in query:
                raise ValueError("Unsupported run parameter")
            body, content_type = export_report(build_run(settings), format_name)
            filename = DOWNLOAD_NAMES[format_name] if url.path == "/api/report" else None
            self.reply(200, body, content_type, filename)
        else:
            # Vite emits a flat, hash-named assets folder; no general filesystem route.
            path = "index.html" if url.path == "/" else url.path.removeprefix("/")
            parts = Path(path).parts
            allowed = path == "index.html" or (len(parts) == 2 and parts[0] == "assets")
            if (
                query
                or not allowed
                or "%" in path
                or "\\" in path
                or any(p.startswith(".") for p in parts)
            ):
                self.reply(404, b"Not found", "text/plain")
                return
            target = self.server.assets / path
            # Resolve symlinks too, so a mistakenly placed link cannot expose source.
            if (
                not target.resolve().is_relative_to(self.server.assets.resolve())
                or target.suffix not in ASSET_TYPES
                or not target.is_file()
            ):
                self.reply(404, b"Not found", "text/plain")
                return
            self.reply(200, target.read_bytes(), ASSET_TYPES[target.suffix])

    def do_POST(self) -> None:
        """Reject all state-changing HTTP methods; CLI history is explicitly local."""
        self.reply(405, b"Read-only application", "text/plain")

    do_PUT = do_POST
    do_DELETE = do_POST
    do_PATCH = do_POST
    do_OPTIONS = do_POST
    do_HEAD = do_POST


def make_server(assets: Path, port: int = 0) -> WorkbenchServer:
    """Create an ephemeral-port loopback service; no caller can select a public interface."""
    server = WorkbenchServer(("127.0.0.1", port), Handler)
    server.assets = assets.resolve()
    return server
