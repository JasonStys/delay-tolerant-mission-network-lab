"""Fixed-path Rust orchestration and optional durable restart handoff by Jason Stys.

Functions: executable, invoke, persist_checkpoint, run_case. Variables: finite wire, checkpoint hashes.
Exact locations: docs/CODE_INDEX.md. No shell, remote process, arbitrary worker path or reference fallback.
"""

import hashlib
import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from typing import Any

from dtnlab.model import Case


def executable() -> Path:
    """Resolve only the trusted checkout release worker or bundled native resource."""
    name = "network-core.exe" if sys.platform == "win32" else "network-core"
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "native" / name
    return Path(__file__).resolve().parents[1] / "target/release" / name


def invoke(wire: str) -> dict[str, Any]:
    """Run one finite request with timeout and strict result envelope, never a Python replacement."""
    if len(wire.encode()) > 16384:
        raise ValueError("Worker envelope too large")
    worker = executable()
    if not worker.is_file():
        raise RuntimeError("Native worker missing; run cargo build --release --locked")
    try:
        result = subprocess.run(
            [str(worker)], input=wire.encode("ascii"), capture_output=True, check=True, timeout=5
        )
        if len(result.stdout) > 1_048_576:
            raise ValueError("Worker result too large")
        value = json.loads(result.stdout)
        if not isinstance(value, dict) or set(value) != {
            "events",
            "samples",
            "messages",
            "checkpoint",
        }:
            raise ValueError("Worker result fields")
        if not isinstance(value["checkpoint"], str) or len(value["checkpoint"]) > 2048:
            raise ValueError("Worker checkpoint field")
        for key, cap in (("events", 20000), ("samples", 64), ("messages", 32)):
            if (
                not isinstance(value[key], list)
                or len(value[key]) > cap
                or any(not isinstance(row, dict) for row in value[key])
            ):
                raise ValueError("Worker rows")
        return value
    except (OSError, subprocess.SubprocessError, ValueError, UnicodeError) as error:
        raise RuntimeError("Native worker failed or returned invalid evidence") from error


def persist_checkpoint(path: Path, wire: str, checkpoint: str) -> str:
    """Write/read the restart boundary through a committed immutable SQLite transaction; hash-check it."""
    identity = hashlib.sha256((wire + checkpoint).encode()).hexdigest()
    with closing(sqlite3.connect(path)) as database, database:
        database.executescript(
            (Path(__file__).parent / "resources/checkpoints.sql").read_text(encoding="utf-8")
        )
        database.execute("BEGIN IMMEDIATE")
        existing = database.execute(
            "SELECT wire,checkpoint FROM checkpoints WHERE id=?", (identity,)
        ).fetchone()
        if existing is None:
            if database.execute("SELECT count(*) FROM checkpoints").fetchone()[0] >= 100:
                raise ValueError("Checkpoint store full")
            database.execute(
                "INSERT INTO checkpoints(id,wire,checkpoint) VALUES(?,?,?)",
                (identity, wire, checkpoint),
            )
    # Reopen after commit: the resumed worker consumes persisted bytes, not an in-memory transaction value.
    with closing(sqlite3.connect(path)) as database:
        row = database.execute(
            "SELECT wire,checkpoint FROM checkpoints WHERE id=?", (identity,)
        ).fetchone()
    if (
        row is None
        or row[0] != wire
        or hashlib.sha256((row[0] + row[1]).encode()).hexdigest() != identity
    ):
        raise ValueError("Checkpoint store hash mismatch")
    return str(row[1])


def run_case(
    case: Case, capacity: int, delay: int, policy: int, store: Path | None = None
) -> dict[str, Any]:
    """Actually restart via a second subprocess; optionally commit/reload its handoff through SQLite."""
    if (
        any(type(value) is not int for value in (capacity, delay, policy))
        or capacity not in (8, 16, 32)
        or delay not in (1, 3, 5)
        or policy not in (0, 1)
    ):
        raise ValueError("Unsupported native settings")
    if store is not None and case.restart_tick == 0:
        raise ValueError("Checkpoint store requires a restart case")
    prefix = invoke(case.wire(capacity, delay, policy, case.restart_tick))
    if case.restart_tick:
        checkpoint = prefix["checkpoint"]
        wire = case.wire(capacity, delay, policy)
        if store is not None:
            checkpoint = persist_checkpoint(store, wire, checkpoint)
        resumed = invoke(wire + "S " + checkpoint + "\n")
        output = {
            "events": prefix["events"]
            + [{"tick": case.restart_tick, "id": 0, "node": 0, "kind": "restart"}]
            + resumed["events"],
            "samples": prefix["samples"] + resumed["samples"],
            "messages": resumed["messages"],
        }
        recovery = {
            "mode": "sqlite-and-fresh-worker" if store else "fresh-worker",
            "next_tick": case.restart_tick,
            "checkpoint_hex": checkpoint,
            "checkpoint_sha256": hashlib.sha256(bytes.fromhex(checkpoint)).hexdigest(),
        }
    else:
        output = {key: prefix[key] for key in ("events", "samples", "messages")}
        recovery = {
            "mode": "none",
            "next_tick": None,
            "checkpoint_hex": None,
            "checkpoint_sha256": None,
        }
    return {**output, "recovery": recovery}
