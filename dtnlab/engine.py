"""Synthetic cases, independent replay gate and deterministic evidence by Jason Stys.

Types/functions: Settings, fixture, catalog, canonical, run_id, analyze, build_run, build_import.
Variables/arguments/fields and exact lines: docs/CODE_INDEX.md. Simulation only; no link or command I/O.
"""

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dtnlab.model import Case, load_case, parse_case
from dtnlab.native import run_case
from dtnlab.reference import simulate

RESOURCES = Path(__file__).parent / "resources"
SCENARIOS = {
    "intermittent-relay": "Intermittent relay",
    "queue-pressure": "Queue and backpressure",
    "expiry-boundary": "Expiry before arrival",
    "corrupt-first": "Corruption and retry",
    "duplicate-copy": "Duplicate copy suppression",
    "restart-inflight": "Restart with in-flight data",
    "priority-choice": "FIFO versus earliest deadline",
    "no-contact": "No contact / retained data",
    "empty-network": "Empty network",
}
CHOICES = {"capacity": (8, 16, 32), "delay": (1, 3, 5), "policy": (0, 1)}
LIMITATIONS = [
    "Invented offline three-node simulation, not BPv7, CBOR, a convergence layer or interoperable space networking.",
    "Ticks and contact windows are synthetic, not actual propagation, radio bandwidth or orbital contact predictions.",
    "Single logical ownership and instantaneous abstract acceptance acknowledgments; no distributed exactly-once guarantee or ACK-loss model.",
    "CRC-32C detects accidental corruption; it does not authenticate, encrypt or provide BPSec.",
    "Atomic worker-boundary restart is tested, not crash consistency during a write, power loss, OS fsync or hardware faults.",
]


@dataclass(frozen=True)
class Settings:
    """Finite queue bytes, latency ticks and ordering policy; zero FIFO, one earliest deadline."""

    scenario: str = "intermittent-relay"
    capacity: int = 16
    delay: int = 3
    policy: int = 0

    def __post_init__(self) -> None:
        """Reject coercion, booleans and unknown finite controls before worker execution."""
        if not isinstance(self.scenario, str) or self.scenario not in SCENARIOS:
            raise ValueError("Unknown case")
        for key, values in CHOICES.items():
            if type(getattr(self, key)) is not int or getattr(self, key) not in values:
                raise ValueError("Unsupported setting")


def canonical(value: Any) -> bytes:
    """Stable complete JSON, forbidding NaN/infinity and excluding machine paths/timing metadata."""
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
    ).encode()


def run_id(run: dict[str, Any]) -> str:
    """Hash all report content except its own identity field; not an authenticated signature."""
    return hashlib.sha256(
        canonical({key: value for key, value in run.items() if key != "id"})
    ).hexdigest()


def fixture(scenario: str) -> Case:
    """Construct invented, independently editable contact/message scenarios with explicit failure modes."""
    if scenario not in SCENARIOS:
        raise ValueError("Unknown fixture")
    messages = [
        {"id": 1, "release": 0, "ttl": 30, "payload_hex": "aabbccdd"},
        {"id": 2, "release": 1, "ttl": 24, "payload_hex": "11223344"},
        {"id": 3, "release": 4, "ttl": 20, "payload_hex": "01020304"},
    ]
    contacts = [
        {"hop": 0, "start": 0, "end": 4},
        {"hop": 0, "start": 10, "end": 15},
        {"hop": 1, "start": 8, "end": 12},
        {"hop": 1, "start": 20, "end": 28},
    ]
    restart = 0
    fault = 0
    if scenario == "queue-pressure":
        messages = [
            {"id": i + 1, "release": i * 2, "ttl": 30, "payload_hex": "ab" * 8} for i in range(8)
        ]
        contacts = [{"hop": 0, "start": 0, "end": 25}, {"hop": 1, "start": 18, "end": 31}]
    elif scenario == "expiry-boundary":
        messages = [{"id": 1, "release": 0, "ttl": 6, "payload_hex": "aabb"}]
        contacts = [{"hop": 0, "start": 0, "end": 1}, {"hop": 1, "start": 3, "end": 4}]
    elif scenario == "corrupt-first":
        fault = 1
    elif scenario == "duplicate-copy":
        fault = 2
    elif scenario == "restart-inflight":
        restart = 2
        fault = 2
    elif scenario == "priority-choice":
        messages = [
            {"id": 1, "release": 0, "ttl": 30, "payload_hex": "aabb"},
            {"id": 2, "release": 0, "ttl": 9, "payload_hex": "1122"},
        ]
        contacts = [{"hop": 0, "start": 0, "end": 2}, {"hop": 1, "start": 5, "end": 6}]
    elif scenario == "no-contact":
        contacts = []
        messages = [{**message, "ttl": 64} for message in messages]
    elif scenario == "empty-network":
        messages = []
        contacts = []
    return parse_case(
        {
            "schema": 1,
            "name": scenario,
            "horizon": 32,
            "restart_tick": restart,
            "fault": fault,
            "messages": messages,
            "contacts": contacts,
        }
    )


def catalog() -> dict[str, Any]:
    """Expose only reviewed scenarios and finite controls; no endpoint, address or executable options."""
    return {"scenarios": SCENARIOS, "choices": CHOICES, "defaults": asdict(Settings())}


def analyze(
    case: Case,
    settings: Settings,
    store: Path | None = None,
    source: str = "invented built-in fixture",
) -> dict[str, Any]:
    """Run real Rust worker(s), require independent Python trace agreement, then summarize all outcomes."""
    native = run_case(case, settings.capacity, settings.delay, settings.policy, store)
    reference = simulate(case, settings.capacity, settings.delay, settings.policy)
    if any(native[key] != reference[key] for key in reference):
        raise RuntimeError("Rust/reference disagreement; evidence withheld")
    counts = Counter(m["status"] for m in native["messages"])
    kinds = Counter(e["kind"] for e in native["events"])
    releases = {message.id: message.release for message in case.messages}
    latencies = [
        m["delivered_tick"] - releases[m["id"]]
        for m in native["messages"]
        if m["status"] == "delivered"
    ]
    result = {
        "schema": 1,
        "name": case.name,
        "input": case.document(),
        "settings": asdict(settings),
        "provenance": {
            "author": "Jason Stys",
            "source": source,
            "native": "dependency-free safe Rust 1.98.1",
            "reference": "independent Python state/CRC replay; all events, samples and final messages agree",
        },
        "limitations": LIMITATIONS,
        "totals": {
            "offered": len(case.messages),
            "delivered": counts["delivered"],
            "expired": counts["expired"],
            "rejected": counts["rejected"],
            "retained": counts["retained"],
            "unreleased": counts["unreleased"],
            "attempts": kinds["sent"],
            "integrity_rejected": kinds["integrity-rejected"],
            "receiver_full": kinds["receiver-full"],
            "duplicates": kinds["duplicate-suppressed"],
            "mean_delivery_ticks": round(sum(latencies) / len(latencies), 9) if latencies else None,
        },
        **native,
    }
    result["id"] = run_id(result)
    return result


def build_run(settings: Settings | None = None, store: Path | None = None) -> dict[str, Any]:
    """Analyze a finite built-in fixture; optional checkpoint store is explicit local CLI-only."""
    settings = settings or Settings()
    return analyze(fixture(settings.scenario), settings, store)


def build_import(path: Path, settings: Settings, store: Path | None = None) -> dict[str, Any]:
    """Validate explicit bounded JSON input and mark its provenance as unverified local simulation data."""
    return analyze(load_case(path), settings, store, "unverified local synthetic input")
