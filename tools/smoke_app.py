"""Actual frozen application/native resource smoke by Jason Stys.

Functions: main, read_output. Variables: process, queue, private temporary reports and real HTTP replies.
Only the explicitly supplied owned bundle is started/stopped. Exact lines: docs/CODE_INDEX.md.
"""

import json
import queue
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path


def main(executable: Path) -> None:
    """Verify two-process checkpoint recovery, committed SQLite and real production HTTP/native assets."""
    executable = executable.resolve(strict=True)
    assert "Vite core license" in (
        executable.parent / "_internal/licenses/vite/LICENSE.md"
    ).read_text(encoding="utf-8")
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
        assert (
            report["totals"]["delivered"] == 3
            and report["recovery"]["mode"] == "sqlite-and-fresh-worker"
            and store.is_file()
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
        assert process.stdout is not None
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
        assert url
        for path in ("api/health", "", "api/run?scenario=restart-inflight"):
            with urllib.request.urlopen(url + path, timeout=5) as response:
                body = response.read()
                if path == "":
                    assert b"Mission Network Lab" in body and b"/assets/" in body
                elif path.startswith("api/run"):
                    assert json.loads(body)["recovery"]["mode"] == "fresh-worker"
                else:
                    assert json.loads(body)["status"] == "ok"
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
