"""CLI, report, SQLite and actual loopback HTTP integration tests by Jason Stys.

Functions: running_server fixture, request helper, test_* contracts.
Variables: temporary paths and reviewed run fixtures. Exact lines: docs/CODE_INDEX.md.
"""

import csv
import io
import json
import sqlite3
import threading
from contextlib import closing
from http.client import HTTPConnection
from pathlib import Path

import pytest

from dtnlab.__main__ import main
from dtnlab.engine import Settings, build_run, run_id
from dtnlab.reports import export_report, save_history
from dtnlab.server import make_server


@pytest.mark.parametrize("format_name", ["json", "csv", "html"])
def test_exports(format_name):
    """Export payloads preserve units/provenance without executing markup or formulas."""
    run = build_run(Settings())
    data, mime = export_report(run, format_name)
    assert data and mime
    if format_name == "json":
        assert json.loads(data) == run
    elif format_name == "csv":
        rows = list(csv.reader(io.StringIO(data.decode())))
        assert len(rows) == len(run["samples"]) + 1
        assert rows[0][0] == "tick"
        assert rows[1][0] == "0"
    else:
        run["name"] = "<script>alert(1)</script>"
        assert b"<script>" not in export_report(run, "html")[0]


def test_formula_safety_and_format():
    """CSV formula cells are neutralized and unsupported formats do not silently degrade."""
    run = build_run(Settings())
    # CSV emits only generated SHA, fixed series/units and numeric fields, not arbitrary text.
    run["name"] = "=HYPERLINK(1)"
    assert "=HYPERLINK" not in export_report(run, "csv")[0].decode()
    with pytest.raises(ValueError):
        export_report(run, "pdf")


def test_history(tmp_path):
    """Content hashing, idempotent inserts, SQL parameters and immutable rows work together."""
    run = build_run(Settings())
    path = tmp_path / "history.sqlite3"
    save_history(path, run)
    save_history(path, run)
    with closing(sqlite3.connect(path)) as database, database:
        assert database.execute("SELECT count(*) FROM runs").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            database.execute("UPDATE runs SET scenario='changed'")
    run["name"] = "'; DROP TABLE runs; --"
    run["id"] = run_id(run)
    save_history(path, run)
    with closing(sqlite3.connect(path)) as database, database:
        assert database.execute("SELECT count(*) FROM runs").fetchone()[0] == 2
    run["name"] = "tampered"
    with pytest.raises(ValueError, match="hash"):
        save_history(path, run)


def test_history_cap(tmp_path):
    """A full history refuses new runs without deleting or replacing existing evidence."""
    path = tmp_path / "history.sqlite3"
    run = build_run(Settings())
    save_history(path, run)
    with closing(sqlite3.connect(path)) as database, database:
        database.executemany(
            "INSERT INTO runs(id,scenario,report_json) VALUES (?, ?, ?)",
            [(str(i).zfill(64), "fixture", "{}") for i in range(99)],
        )
    with pytest.raises(ValueError, match="History full"):
        save_history(path, build_run(Settings(capacity=32)))


def test_cli(tmp_path, capsys):
    """CLI exports and local history work without a browser and never overwrite output."""
    output = tmp_path / "evidence.json"
    args = [
        "export",
        "--scenario",
        "intermittent-relay",
        "--output",
        str(output),
        "--history",
        str(tmp_path / "runs.sqlite3"),
    ]
    assert main(args) == 0
    assert json.loads(output.read_bytes())["name"] == "intermittent-relay"
    assert main(args) == 1
    assert "already exists" in capsys.readouterr().err
    assert (
        main(
            [
                "export",
                "--scenario",
                "intermittent-relay",
                "--output",
                str(tmp_path / "missing" / "x"),
            ]
        )
        == 1
    )


def test_input_cli_roundtrip(tmp_path):
    """The actual CLI exports reusable input, imports it and persists matching full evidence."""
    capture = tmp_path / "input.json"
    output = tmp_path / "imported.json"
    history = tmp_path / "imported.sqlite3"
    assert (
        main(
            [
                "export",
                "--scenario",
                "intermittent-relay",
                "--format",
                "input",
                "--output",
                str(capture),
            ]
        )
        == 0
    )
    assert (
        main(
            ["export", "--input", str(capture), "--output", str(output), "--history", str(history)]
        )
        == 0
    )
    result = json.loads(output.read_bytes())
    assert result["name"] == "intermittent-relay"
    assert result["totals"]["delivered"] == 3
    assert result["provenance"]["source"] == "unverified local synthetic input"
    with closing(sqlite3.connect(history)) as database:
        assert database.execute("SELECT id FROM runs").fetchone() == (result["id"],)


def test_concurrent_capacity(tmp_path):
    """Two simultaneous writers cannot both consume the last slot or exceed the 100-row cap."""
    from concurrent.futures import ThreadPoolExecutor

    path = tmp_path / "concurrent.sqlite3"
    save_history(path, build_run(Settings()))
    with closing(sqlite3.connect(path)) as database, database:
        database.executemany(
            "INSERT INTO runs(id,scenario,report_json) VALUES(?,?,?)",
            [(str(i).zfill(64), "fixture", "{}") for i in range(98)],
        )
    barrier = threading.Barrier(2)

    def insert(capacity):
        """Coordinate attempts with distinct valid reports and return the observed capacity result."""
        run = build_run(Settings(capacity=capacity))
        barrier.wait(timeout=5)
        try:
            save_history(path, run)
            return "inserted"
        except ValueError as error:
            assert "History full" in str(error)
            return "full"

    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = list(workers.map(insert, [8, 32]))
    assert sorted(outcomes) == ["full", "inserted"]
    with closing(sqlite3.connect(path)) as database:
        assert database.execute("SELECT count(*) FROM runs").fetchone()[0] == 100


def test_cli_serve(monkeypatch, tmp_path):
    """Launch and graceful Ctrl-C paths use loopback, including optional browser launch."""
    (tmp_path / "web" / "dist").mkdir(parents=True)
    (tmp_path / "web" / "dist" / "index.html").write_text("test")
    monkeypatch.setattr("dtnlab.__main__.sys._MEIPASS", str(tmp_path), raising=False)
    opened = []
    monkeypatch.setattr("dtnlab.__main__.webbrowser.open", opened.append)

    def interrupt(*args, **kwargs):
        """Avoid an infinite serve loop while testing the CLI's shutdown path."""
        raise KeyboardInterrupt

    monkeypatch.setattr("dtnlab.server.WorkbenchServer.serve_forever", interrupt)
    assert main(["serve"]) == 0
    assert opened[0].startswith("http://127.0.0.1:")
    assert main(["serve", "--no-browser"]) == 0
    (tmp_path / "web" / "dist" / "index.html").unlink()
    assert main(["serve"]) == 1


def test_cli_database_failure(tmp_path, capsys):
    """A missing history parent gives a controlled CLI failure, not an unhandled traceback."""
    assert (
        main(
            [
                "export",
                "--scenario",
                "intermittent-relay",
                "--output",
                str(tmp_path / "evidence.json"),
                "--history",
                str(tmp_path / "missing" / "history.sqlite3"),
            ]
        )
        == 1
    )
    assert "Cannot complete operation" in capsys.readouterr().err
    assert not (tmp_path / "evidence.json").exists()


@pytest.fixture
def running_server(tmp_path):
    """Run the production handler on a real ephemeral loopback socket with isolated assets."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>Test</title>")
    (tmp_path / "assets" / "bundle.js").write_text("console.log('test')")
    server = make_server(tmp_path)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    yield server
    server.shutdown()
    server.server_close()
    worker.join(timeout=3)


def request(server, path="/api/health", method="GET", headers=None):
    """Return status/headers/body through an actual HTTP client, without following redirects."""
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    connection.request(method, path, headers=headers or {})
    response = connection.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    connection.close()
    return result


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/assets/bundle.js",
        "/api/health",
        "/api/catalog",
        "/api/run?scenario=intermittent-relay&capacity=16",
        "/api/report?format=html",
    ],
)
def test_http_success(running_server, path):
    """Production routes serve useful evidence and a strict header policy without CORS."""
    status, headers, body = request(running_server, path)
    assert status == 200 and body
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "Access-Control-Allow-Origin" not in headers
    if "report" in path:
        assert "attachment" in headers["Content-Disposition"]


@pytest.mark.parametrize(
    "path",
    [
        "/.git/config",
        "/dtnlab/engine.py",
        "/assets/../index.html",
        "/assets/%2e%2e",
        "/assets/x.txt",
        "/assets/no.js",
        "/?x=1",
        "/assets\\bad.js",
    ],
)
def test_http_path_rejection(running_server, path):
    """The service never becomes a general source/hidden-file browser."""
    assert request(running_server, path)[0] == 404


def test_fixed_download_headers(running_server):
    """Download names never reflect request text, including encoded header delimiters."""
    _, headers, _ = request(running_server, "/api/report?scenario=intermittent-relay&format=json")
    assert headers["Content-Disposition"] == 'attachment; filename="mission-network-evidence.json"'
    status, headers, _ = request(running_server, "/api/report?format=json%0D%0AX-Injected%3Ayes")
    assert status == 400 and "X-Injected" not in headers


@pytest.mark.parametrize(
    "query",
    [
        "capacity=-1",
        "capacity=nan",
        "capacity=900",
        "scenario=unknown",
        "capacity=16&capacity=32",
        "x=1",
        "format=html",
        "a=1&b=2&c=3&d=4&e=5&f=6&g=7&h=8&i=9",
    ],
)
def test_http_query_rejection(running_server, query):
    """Unreviewed, duplicate or excessive parameters fail closed with no tracebacks."""
    status, _, body = request(running_server, "/api/run?" + query)
    assert status == 400
    assert b"Traceback" not in body


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "attacker.example"},
        {"Origin": "https://evil.example"},
        {"Sec-Fetch-Site": "cross-site"},
    ],
)
def test_http_rebinding_and_origin(running_server, headers):
    """DNS rebinding, cross-origin fetch and cross-site top-level attempts are rejected."""
    assert request(running_server, headers=headers)[0] == 403


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
def test_no_mutations(running_server, method):
    """HTTP intentionally has no data mutation endpoints."""
    assert request(running_server, method=method)[0] == 405


def test_long_request_and_resource_failure(running_server, monkeypatch):
    """Bounded requests and unavailable local resources return generic errors."""
    assert request(running_server, "/" + "a" * 1200)[0] == 414

    def broken(*args):
        """Simulate a missing packaged resource without exposing the local path."""
        raise OSError("secret local path")

    monkeypatch.setattr("dtnlab.server.build_run", broken)
    status, _, body = request(running_server, "/api/run")
    assert status == 500 and b"secret" not in body


def test_symlink_escape(running_server, tmp_path):
    """Resolved paths cannot leave the build directory, even if a symlink was placed there."""
    # Mock only resolution: Windows symlink creation requires a privilege not needed by the app.
    outside = tmp_path.parent / "secret.js"
    original = Path.resolve
    from unittest.mock import patch

    with patch.object(
        Path,
        "resolve",
        lambda p, *a, **k: outside if p.name == "escape.js" else original(p, *a, **k),
    ):
        assert request(running_server, "/assets/escape.js")[0] == 404


@pytest.mark.parametrize("phase", ["headers", "body"])
def test_disconnected_response_is_not_retried(monkeypatch, phase):
    """An aborted peer during headers/body returns quietly, without a second error response."""
    from io import BytesIO

    from dtnlab.server import Handler

    handler = Handler.__new__(Handler)
    handler.command = "GET"
    responses = []
    monkeypatch.setattr(handler, "send_response", responses.append)
    monkeypatch.setattr(handler, "send_header", lambda *args: None)
    monkeypatch.setattr(handler, "end_headers", lambda: None)
    handler.wfile = BytesIO()

    def disconnected(*args):
        """Reproduce a closed local TCP peer without depending on OS socket timing."""
        raise ConnectionAbortedError("client canceled")

    if phase == "headers":
        monkeypatch.setattr(handler, "end_headers", disconnected)
    else:
        monkeypatch.setattr(handler.wfile, "write", disconnected)
    handler.reply(200, b"evidence", "application/json")
    assert responses == [200]
    handler.wfile.close()
