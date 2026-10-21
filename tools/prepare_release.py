"""Fail-closed draft release preparation by Jason Stys.

Function: main. Variables: version, sha, repository, workflow runs. Index: docs/CODE_INDEX.md.
Only the exact current commit's successful Validation and CodeQL runs authorize packaging.
"""

import json
import os
import re
import subprocess


def main() -> None:
    """Validate version, require successful exact-commit workflows, create a new draft only."""
    version = os.environ["VERSION"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise SystemExit("Expected digits.digits.digits")
    sha, repository = os.environ["GITHUB_SHA"], os.environ["GITHUB_REPOSITORY"]
    for workflow in ("validate.yml", "codeql.yml"):
        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repository}/actions/workflows/{workflow}/runs?head_sha={sha}&per_page=20",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        runs = json.loads(result.stdout)["workflow_runs"]
        if not runs or runs[0]["conclusion"] != "success":
            raise SystemExit(f"{workflow} has not passed at {sha}")
    subprocess.run(
        [
            "gh",
            "release",
            "create",
            f"v{version}",
            "--repo",
            repository,
            "--target",
            sha,
            "--draft",
            "--title",
            f"Delay Tolerant Mission Network Lab v{version}",
            "--notes",
            "Unsigned portable network-simulation bundles by Jason Stys. Extract the entire ZIP. Invented offline topology, not BPv7 interoperability, BPSec or flight-qualified networking. Verify SHA-256; do not bypass OS warnings. See validation and user guide.",
        ],
        check=True,
        timeout=30,
    )


if __name__ == "__main__":
    main()
