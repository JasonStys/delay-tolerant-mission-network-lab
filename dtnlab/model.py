"""Strict bounded synthetic network schema by Jason Stys.

Types: Message, Contact, Case. Functions: number, fields, parse_case, load_case.
All variable/argument lines: docs/CODE_INDEX.md. Ticks are dimensionless lab time, not flight time.
"""

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

MAX_BYTES = 65536


def number(value: Any, minimum: int, maximum: int) -> int:
    """Require bounded actual integers, excluding bool, float, string and overflow/coercion."""
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("Invalid integer")
    return value


def fields(value: Any, keys: set[str]) -> dict[str, Any]:
    """Require exact object keys so unsupported fields are never silently discarded."""
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("Unexpected object fields")
    return value


@dataclass(frozen=True)
class Message:
    """Immutable source message; unique id, release tick, relative TTL and 1..16 opaque payload bytes."""

    id: int
    release: int
    ttl: int
    payload_hex: str


@dataclass(frozen=True)
class Contact:
    """A directed hop's half-open departure interval; not radio geometry or predicted real contact."""

    hop: int
    start: int
    end: int


@dataclass(frozen=True)
class Case:
    """Invented three-node topology; restart is a boundary before that tick's phases, zero means none."""

    name: str
    horizon: int
    restart_tick: int
    fault: int
    messages: tuple[Message, ...]
    contacts: tuple[Contact, ...]

    def document(self) -> dict[str, Any]:
        """Return genuine JSON lists and schema version, without machine paths or trusted-source claims."""
        return {
            "schema": 1,
            "name": self.name,
            "horizon": self.horizon,
            "restart_tick": self.restart_tick,
            "fault": self.fault,
            "messages": [asdict(m) for m in self.messages],
            "contacts": [asdict(c) for c in self.contacts],
        }

    def wire(self, capacity: int, delay: int, policy: int, pause: int = 0) -> str:
        """Encode the finite native lab envelope; no addresses, shell parameters or file paths."""
        lines = [f"DTN1 {self.horizon} {capacity} {delay} {policy} {self.fault} {pause}"]
        lines.extend(f"M {m.id} {m.release} {m.ttl} {m.payload_hex}" for m in self.messages)
        lines.extend(f"C {c.hop} {c.start} {c.end}" for c in self.contacts)
        return "\n".join(lines) + "\n"


def parse_case(value: Any) -> Case:
    """Validate JSON ranges, identity uniqueness and nonoverlapping per-hop windows before simulation."""
    row = fields(
        value, {"schema", "name", "horizon", "restart_tick", "fault", "messages", "contacts"}
    )
    if type(row["schema"]) is not int or row["schema"] != 1:
        raise ValueError("Unsupported schema")
    if not isinstance(row["name"], str) or not re.fullmatch(
        r"[a-z0-9][a-z0-9-]{0,47}", row["name"]
    ):
        raise ValueError("Invalid name")
    horizon = number(row["horizon"], 1, 64)
    restart = number(row["restart_tick"], 0, horizon - 1)
    fault = number(row["fault"], 0, 2)
    if (
        not isinstance(row["messages"], list)
        or len(row["messages"]) > 32
        or not isinstance(row["contacts"], list)
        or len(row["contacts"]) > 32
    ):
        raise ValueError("Record limits")
    messages = []
    for value in row["messages"]:
        item = fields(value, {"id", "release", "ttl", "payload_hex"})
        payload = item["payload_hex"]
        if not isinstance(payload, str) or not re.fullmatch(r"(?:[a-fA-F0-9]{2}){1,16}", payload):
            raise ValueError("Payload must be 1..16 hex bytes")
        messages.append(
            Message(
                number(item["id"], 1, 32),
                number(item["release"], 0, horizon - 1),
                number(item["ttl"], 1, 64),
                payload.lower(),
            )
        )
    contacts = []
    for value in row["contacts"]:
        item = fields(value, {"hop", "start", "end"})
        hop = number(item["hop"], 0, 1)
        start = number(item["start"], 0, horizon - 1)
        end = number(item["end"], start + 1, horizon)
        contacts.append(Contact(hop, start, end))
    messages.sort(key=lambda m: m.id)
    contacts.sort(key=lambda c: (c.hop, c.start, c.end))
    if len({m.id for m in messages}) != len(messages):
        raise ValueError("Duplicate message id")
    for left, right in zip(contacts, contacts[1:], strict=False):
        if left.hop == right.hop and right.start < left.end:
            raise ValueError("Overlapping contacts")
    return Case(row["name"], horizon, restart, fault, tuple(messages), tuple(contacts))


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON object keys instead of last-write-wins reinterpretation."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def load_case(path: Path) -> Case:
    """Read at most 64 KiB plus one sentinel; malformed UTF-8/nesting/JSON gets a controlled failure."""
    with path.open("rb") as source:
        body = source.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError("Input exceeds 64 KiB")
    try:
        return parse_case(json.loads(body.decode("utf-8"), object_pairs_hook=unique_object))
    except (UnicodeError, RecursionError) as error:
        raise ValueError("Invalid JSON envelope") from error
