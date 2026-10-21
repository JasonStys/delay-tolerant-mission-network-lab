"""Local website launcher and reproducible export CLI by Jason Stys.

Function: main. Variables: arguments, bounded case, export, history and loopback service.
Exact definition and variable lines: docs/CODE_INDEX.md. Never overwrite an export.
"""

import argparse
import sqlite3
import sys
import webbrowser
from pathlib import Path

from dtnlab.engine import CHOICES, SCENARIOS, Settings, build_import, build_run
from dtnlab.reports import export_report, save_history
from dtnlab.server import make_server


def main(argv: list[str] | None = None) -> int:
    """Serve protected read-only loopback UI or explicitly save deterministic local evidence."""
    parser = argparse.ArgumentParser(description="Delay Tolerant Mission Network Lab by Jason Stys")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Open the local browser application")
    serve.add_argument("--port", type=int, default=0)
    serve.add_argument("--no-browser", action="store_true")
    export = commands.add_parser("export", help="Export deterministic evidence")
    export.add_argument("--scenario", choices=SCENARIOS, default=Settings().scenario)
    for key, choices in CHOICES.items():
        export.add_argument("--" + key, type=int, choices=choices, default=getattr(Settings(), key))
    export.add_argument("--format", choices=("json", "csv", "html", "input"), default="json")
    export.add_argument("--input", type=Path)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--history", type=Path)
    export.add_argument("--checkpoint-store", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            settings = Settings(**{key: getattr(args, key) for key in ("scenario", *CHOICES)})
            run = (
                build_import(args.input, settings, args.checkpoint_store)
                if args.input
                else build_run(settings, args.checkpoint_store)
            )
            body, _ = export_report(run, args.format)
            if args.output.exists():
                raise FileExistsError("Export destination already exists")
            if args.history:
                save_history(args.history, run)
            with args.output.open("xb") as destination:
                destination.write(body)
            print(f"Saved {run['id']}")
            return 0
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        assets = root / "web/dist"
        if not (assets / "index.html").is_file():
            raise OSError("Build the website first: npm ci and npm run build")
        with make_server(assets, args.port) as server:
            url = f"http://127.0.0.1:{server.server_port}/"
            print(f"Delay Tolerant Mission Network Lab by Jason Stys\n{url}", flush=True)
            if not args.no_browser:
                webbrowser.open(url)
            try:
                server.serve_forever(poll_interval=0.25)
            except KeyboardInterrupt:
                print("Mission network lab stopped.", flush=True)
        return 0
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
        print(f"Cannot complete operation: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
