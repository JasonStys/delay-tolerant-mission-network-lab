"""Strict JSON/tick/range envelope and native bridge failure tests by Jason Stys.

Functions: document, test_* contracts. Variables: explicit bad values, fake worker results and bounded input.
No untrusted code executes. Exact line inventory: docs/CODE_INDEX.md.
"""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from dtnlab.engine import Settings, build_import, fixture
from dtnlab.model import MAX_BYTES, load_case, parse_case
from dtnlab.native import executable, invoke, run_case


def document():
    """Return independent mutable JSON rows from the actual invented fixture."""
    return fixture("intermittent-relay").document()


@pytest.mark.parametrize(
    "key,value",
    [
        ("schema", True),
        ("schema", 2),
        ("name", "<script>"),
        ("name", "a" * 49),
        ("horizon", 0),
        ("horizon", 65),
        ("horizon", 32.0),
        ("restart_tick", 32),
        ("fault", 3),
        ("messages", {}),
        ("contacts", [{}]),
    ],
)
def test_root_contract(key, value):
    """Exact root schema rejects coercion, range and container errors."""
    case = document()
    case[key] = value
    with pytest.raises(ValueError):
        parse_case(case)


@pytest.mark.parametrize(
    "kind,key,value",
    [
        ("messages", "id", True),
        ("messages", "id", 33),
        ("messages", "ttl", 0),
        ("messages", "release", 32),
        ("messages", "payload_hex", ""),
        ("messages", "payload_hex", "f"),
        ("messages", "payload_hex", "00" * 17),
        ("messages", "payload_hex", "zz"),
        ("messages", "extra", 1),
        ("contacts", "hop", 2),
        ("contacts", "end", 0),
        ("contacts", "start", 32),
        ("contacts", "end", 33),
    ],
)
def test_record_contract(kind, key, value):
    """Message/contact records never silently reinterpret unknown fields or invalid ranges."""
    case = document()
    case[kind][0][key] = value
    with pytest.raises(ValueError):
        parse_case(case)


def test_duplicate_overlap_and_limits():
    """Ambiguous identities/windows, oversized arrays and unknown roots are rejected."""
    for kind in ("messages", "contacts"):
        case = document()
        case[kind].append(case[kind][0])
        with pytest.raises(ValueError):
            parse_case(case)
        case = document()
        case[kind] *= 33
        with pytest.raises(ValueError):
            parse_case(case)
    case = document()
    case["extra"] = 1
    with pytest.raises(ValueError):
        parse_case(case)


def test_order_and_uppercase():
    """Canonical JSON input normalizes record order and equivalent uppercase hex without data loss."""
    case = document()
    expected = parse_case(case)
    case["messages"].reverse()
    case["contacts"].reverse()
    case["messages"][0]["payload_hex"] = case["messages"][0]["payload_hex"].upper()
    assert parse_case(case) == expected


def test_bounded_import(tmp_path):
    """Whole input bounds, duplicate keys, nesting/encoding and explicit local provenance are tested."""
    path = tmp_path / "input.json"
    path.write_text(json.dumps(document()), encoding="utf-8")
    assert (
        build_import(path, Settings())["provenance"]["source"] == "unverified local synthetic input"
    )
    for body in (
        b"{}",
        b'{"schema":1,"schema":1}',
        b"\xff",
        b"[" * 1100 + b"]" * 1100,
        b" " * (MAX_BYTES + 1),
    ):
        path.write_bytes(body)
        with pytest.raises(ValueError):
            load_case(path)


def test_missing_worker_and_worker_failure(monkeypatch, tmp_path):
    """Missing/failed worker never triggers a Python-only success fallback."""
    monkeypatch.setattr("dtnlab.native.executable", lambda: tmp_path / "missing.exe")
    with pytest.raises(RuntimeError, match="missing"):
        invoke("DTN1 32 8 1 0 0 0\n")
    monkeypatch.setattr("dtnlab.native.executable", lambda: Path(__file__))

    def failed(*args, **kwargs):
        """Simulate process timeout without spawning arbitrary downloaded/untrusted software."""
        raise subprocess.TimeoutExpired("trusted-worker", 5)

    monkeypatch.setattr("dtnlab.native.subprocess.run", failed)
    with pytest.raises(RuntimeError):
        invoke("DTN1 32 8 1 0 0 0\n")


@pytest.mark.parametrize(
    "body",
    [
        b"{}",
        b"not-json",
        b"[]",
        b"x" * 1048577,
        b'{"events":[],"samples":[],"messages":[],"checkpoint":1}',
        b'{"events":null,"samples":[],"messages":[],"checkpoint":"00"}',
    ],
    ids=["object", "not-json", "array", "oversized-output", "checkpoint-type", "rows-type"],
)
def test_worker_result_contract(monkeypatch, body):
    """Invalid/malformed/oversized worker output fails as unavailable evidence."""
    monkeypatch.setattr("dtnlab.native.executable", lambda: Path(__file__))
    monkeypatch.setattr(
        "dtnlab.native.subprocess.run", lambda *args, **kwargs: SimpleNamespace(stdout=body)
    )
    with pytest.raises(RuntimeError):
        invoke("DTN1 32 8 1 0 0 0\n")


def test_bundled_worker_path_and_unknown_fixture(monkeypatch, tmp_path):
    """Bundled resource selection is fixed, and unknown fixture names fail before execution."""
    monkeypatch.setattr("dtnlab.native.sys._MEIPASS", str(tmp_path), raising=False)
    assert executable().parent == tmp_path / "native"
    with pytest.raises(ValueError, match="Unknown"):
        fixture("unknown")


@pytest.mark.parametrize("capacity,delay,policy", [(16, 3, True), (8.0, 3, 0), (8, 2, 0)])
def test_native_setting_contract(capacity, delay, policy):
    """The direct internal bridge rejects type coercions as strictly as public settings."""
    with pytest.raises(ValueError, match="Unsupported"):
        run_case(fixture("intermittent-relay"), capacity, delay, policy)
