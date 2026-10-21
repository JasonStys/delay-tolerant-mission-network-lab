"""Portable application entry point by Jason Stys; main and argv: docs/CODE_INDEX.md.

Double-click opens the loopback UI. No admin rights, installer hooks or background service.
"""

import sys

from dtnlab.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or ["serve"]))
