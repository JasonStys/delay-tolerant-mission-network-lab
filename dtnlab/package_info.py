"""Read bounded frozen-build identity by Jason Stys, never a user-profile configuration.

Function: package_info. Variables: bundled metadata path and exact version/source fields.
Source mode has no packaged identity. Exact declarations: docs/CODE_INDEX.md.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

from dtnlab import __version__


def package_info() -> dict[str, Any] | None:
    """Require coherent embedded metadata in frozen mode; no source fallback for a broken bundle."""
    if not getattr(sys, "frozen", False):
        return None
    path = Path(__file__).with_name("resources") / "RELEASE.json"
    if not path.is_file() or path.stat().st_size > 4096:
        raise ValueError("Packaged release identity missing")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "schema_version",
            "name",
            "version",
            "source_commit",
            "source_dirty",
            "platform",
            "machine",
        }
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["name"] != "delay-tolerant-mission-network-lab"
        or value["version"] != __version__
        or not isinstance(value["source_commit"], str)
        or re.fullmatch(r"[a-f0-9]{40}", value["source_commit"]) is None
        or type(value["source_dirty"]) is not bool
        or value["platform"] not in {"windows", "linux", "darwin"}
        or not isinstance(value["machine"], str)
        or re.fullmatch(r"[a-z0-9_]+", value["machine"]) is None
    ):
        raise ValueError("Packaged release identity invalid")
    return value
