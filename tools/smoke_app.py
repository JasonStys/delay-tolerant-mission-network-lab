"""Actual extracted-executable CLI, HTTP and Chromium acceptance by Jason Stys.

Functions: main, checked_run. Variables: owned child, random instance marker and temporary exports.
Exact lines: docs/CODE_INDEX.md. No retries, source fallback, account or user-server reuse.
"""

import json
import os
import queue
import re
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

if __package__:
    from .legacy_smoke import main as legacy_main
    from .release_contract import ROOT, configuration, require
else:
    from legacy_smoke import main as legacy_main
    from release_contract import ROOT, configuration, require


class RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """A local application check never follows an HTTP redirect to another listener or origin."""

    def redirect_request(self, *args, **kwargs):
        """Abort before urllib can issue the redirected request."""
        raise ValueError("Local native acceptance refuses redirects")


def checked_run(value: dict, version: str) -> None:
    """Check independently expected new-feature evidence from the actual compiled app."""
    require(len(value["waterfalls"]) == 3, "Missing complete-run waterfall")
    require(
        sum(row["bottlenecks"]["integrity_rejected_events"] for row in value["waterfalls"]) == 1,
        "Wrong corruption witness",
    )
    for row in value["waterfalls"]:
        require(
            row["queue_ticks"] + row["in_flight_ticks"] == row["observed_elapsed_ticks"],
            "Latency does not reconcile",
        )


def main(executable: Path) -> None:
    """Use a fresh cwd/profile; child binds port0, health must echo this invocation's random marker."""
    executable = executable.resolve(strict=True)
    expected = json.loads((executable.parent / "RELEASE.json").read_text(encoding="utf-8"))
    require(expected["version"] == configuration()["version"], "Extracted version mismatch")
    environment = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")}
    nonce = secrets.token_hex(16)
    environment["PORTABLE_SMOKE_NONCE"] = nonce
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), RefuseRedirects())
    with tempfile.TemporaryDirectory(
        prefix="delay-tolerant-mission-network-lab-native-journey-"
    ) as temporary:
        output = Path(temporary) / "native-export.json"
        command = [
            str(executable),
            "export",
            "--scenario",
            "corrupt-first",
            "--output",
            str(output),
        ]
        subprocess.run(command, cwd=temporary, env=environment, check=True, timeout=30)
        checked_run(json.loads(output.read_bytes()), expected["version"])
        before = output.read_bytes()
        repeat = subprocess.run(
            command, cwd=temporary, env=environment, capture_output=True, timeout=30
        )
        require(
            repeat.returncode != 0 and output.read_bytes() == before,
            "Existing export was overwritten",
        )
        process = subprocess.Popen(
            [str(executable), "serve", "--port", "0", "--no-browser"],
            cwd=temporary,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        )
        lines: queue.Queue[str] = queue.Queue()

        def read_output() -> None:
            """Read only this child's output; queue deadlines bound readiness without sleeping."""
            if process.stdout:
                for line in process.stdout:
                    lines.put(line.strip())

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        try:
            deadline, url = time.monotonic() + 30, ""
            while not url:
                remaining = deadline - time.monotonic()
                require(remaining > 0, "Frozen app readiness deadline exceeded")
                try:
                    line = lines.get(timeout=remaining)
                except queue.Empty as error:
                    raise RuntimeError(
                        "Frozen app did not announce an owned loopback URL"
                    ) from error
                if line.startswith("http://"):
                    require(
                        re.fullmatch(r"http://127\.0\.0\.1:[0-9]{4,5}/", line) is not None,
                        "Unexpected frozen-app URL",
                    )
                    url = line
            require(process.poll() is None, "Frozen app exited before acceptance")

            def fetch(route: str) -> bytes:
                """No redirects or outside requests; every probe stays on the owned child origin."""
                with opener.open(url + route, timeout=8) as response:
                    require(
                        response.status == 200 and response.geturl() == url + route,
                        "Unexpected HTTP response",
                    )
                    body = response.read(2 * 1024 * 1024 + 1)
                    require(len(body) <= 2 * 1024 * 1024, "Native response exceeds read budget")
                    return body

            health = json.loads(fetch("api/health"))
            require(
                health["status"] == "ok"
                and health["version"] == expected["version"]
                and health["instance"] == nonce
                and health["package"] == expected,
                "Wrong packaged process/identity",
            )
            html = fetch("").decode()
            require("Mission Network Lab · Jason Stys" in html, "Wrong compiled application HTML")
            assets = re.findall(r'(?:src|href)="(/assets/[A-Za-z0-9_.-]+\.(?:js|css))"', html)
            require(
                any(asset.endswith(".js") for asset in assets), "Actual compiled UI script missing"
            )
            for asset in assets:
                require(bool(fetch(asset.lstrip("/"))), "Compiled asset is empty")
            checked_run(json.loads(fetch("api/run?scenario=corrupt-first")), expected["version"])
            subprocess.run(
                [
                    "node",
                    str(ROOT / "tools/native_feature_smoke.mjs"),
                    url,
                    temporary,
                    expected["version"],
                ],
                cwd=temporary,
                env=environment,
                check=True,
                timeout=45,
            )
            print("Extracted native CLI, owned process, compiled assets and real UI/export passed")
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

    legacy_main(executable)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
