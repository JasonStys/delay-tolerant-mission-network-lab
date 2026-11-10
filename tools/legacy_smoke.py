"""Actual frozen application/native resource smoke by Jason Stys.

Functions: main, read_output. Variables: process, queue, private temporary reports and real HTTP replies.
Only the explicitly supplied owned bundle is started/stopped. Exact lines: docs/CODE_INDEX.md.
Preserved domain acceptance; canonical process/version/browser proof is in smoke_app.py."""

import json
import queue
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

if __package__:
    from .release_contract import require
else:
    from release_contract import require


class RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """A local application check never follows an HTTP redirect to another listener or origin."""

    def redirect_request(self, *args, **kwargs):
        """Abort before urllib can issue the redirected request."""
        raise ValueError("Local native acceptance refuses redirects")


OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), RefuseRedirects())


def main(executable: Path) -> None:
    """Verify two-process checkpoint recovery, committed SQLite and real production HTTP/native assets."""
    executable = executable.resolve(strict=True)
    require(
        bool(
            "Vite core license"
            in (executable.parent / "_internal/licenses/vite/LICENSE.md").read_text(
                encoding="utf-8"
            )
        ),
        "Preserved native acceptance check failed",
    )
    with tempfile.TemporaryDirectory(prefix="dtn-smoke-") as directory:
        output = Path(directory) / "report.json"
        store = Path(directory) / "checkpoints.sqlite3"
        subprocess.run(
            [
                str(executable),
                "export",
                "--scenario",
                "restart-inflight",
                "--output",
                str(output),
                "--checkpoint-store",
                str(store),
            ],
            check=True,
            timeout=30,
        )
        report = json.loads(output.read_bytes())
        require(
            bool(
                report["totals"]["delivered"] == 3
                and report["recovery"]["mode"] == "sqlite-and-fresh-worker"
                and store.is_file()
            ),
            "Preserved native acceptance check failed",
        )
    process = subprocess.Popen(
        [str(executable), "serve", "--no-browser"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    lines: queue.Queue[str] = queue.Queue()

    def read_output() -> None:
        """Read child output off the main thread so startup remains timeout-bounded."""
        require(bool(process.stdout is not None), "Preserved native acceptance check failed")
        for line in process.stdout:
            lines.put(line.strip())

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    try:
        url = ""
        for _ in range(5):
            line = lines.get(timeout=15)
            if line.startswith("http://127.0.0.1:"):
                url = line
                break
        require(bool(url), "Preserved native acceptance check failed")
        for path in ("api/health", "", "api/run?scenario=restart-inflight"):
            with OPENER.open(url + path, timeout=5) as response:
                body = response.read()
                if path == "":
                    require(
                        bool(b"Mission Network Lab" in body and b"/assets/" in body),
                        "Preserved native acceptance check failed",
                    )
                elif path.startswith("api/run"):
                    require(
                        bool(json.loads(body)["recovery"]["mode"] == "fresh-worker"),
                        "Preserved native acceptance check failed",
                    )
                else:
                    require(
                        bool(json.loads(body)["status"] == "ok"),
                        "Preserved native acceptance check failed",
                    )
        print(
            "Frozen app: native Rust/reference, fresh-process restart, committed checkpoint, export and web assets/API passed"
        )
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        reader.join(timeout=3)
        if process.stdout:
            process.stdout.close()


if __name__ == "__main__":
    main(Path(sys.argv[1]))
