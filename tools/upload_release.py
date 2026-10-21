"""Upload only a freshly smoke-tested native bundle to its draft by Jason Stys.

Function: main. Variables: version/repository/metadata/assets. Index: docs/CODE_INDEX.md.
The workflow never publishes or replaces a public release asset.
"""

import json
import os
import re
import subprocess
from pathlib import Path


def main() -> None:
    """Refuse malformed versions, public releases and missing bundles before transmission."""
    version, repository = os.environ["VERSION"], os.environ["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise SystemExit("Invalid version")
    result = subprocess.run(
        ["gh", "release", "view", f"v{version}", "--repo", repository, "--json", "isDraft"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if not json.loads(result.stdout)["isDraft"]:
        raise SystemExit("Upload target is not a draft")
    assets = sorted(Path("dist").glob("delay-tolerant-mission-network-lab-*.*"))
    if len(assets) != 2 or {p.suffix for p in assets} != {".zip", ".sha256"}:
        raise SystemExit("Expected exactly one verified ZIP/checksum pair")
    subprocess.run(
        ["gh", "release", "upload", f"v{version}", "--repo", repository, *map(str, assets)],
        check=True,
        timeout=120,
    )


if __name__ == "__main__":
    main()
