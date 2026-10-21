"""Independent declarative Python network oracle by Jason Stys.

Functions: crc32c, simulate. Variables: table, ownership dictionaries, flights and stable event phases.
Exact locations: docs/CODE_INDEX.md. Not a fallback: production evidence requires actual Rust agreement.
"""

from functools import cache
from typing import Any

from dtnlab.model import Case


@cache
def crc_table() -> tuple[int, ...]:
    """Build the immutable table once; subsequent payload checks are linear in their byte count."""
    table = []
    for value in range(256):
        for _ in range(8):
            value = (value >> 1) ^ (0x82F63B78 if value & 1 else 0)
        table.append(value)
    return tuple(table)


def crc32c(payload: bytes) -> int:
    """Table-driven CRC-32C, independently structured from the Rust per-bit payload loop."""
    table = crc_table()
    state = 0xFFFFFFFF
    for byte in payload:
        state = table[(state ^ byte) & 255] ^ (state >> 8)
    return state ^ 0xFFFFFFFF


def simulate(case: Case, capacity: int, delay: int, policy: int) -> dict[str, Any]:
    """Reconstruct expected trace from immutable messages and per-id dictionaries, not native state bytes."""
    messages = {m.id: m for m in case.messages}
    status = {key: "unreleased" for key in messages}
    owner = dict.fromkeys(messages, 0)
    busy = dict.fromkeys(messages, False)
    attempts = {key: [0, 0] for key in messages}
    delivered = dict.fromkeys(messages, -1)
    flights: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    samples = []

    def used(node: int) -> int:
        """Account retained bytes by current logical owner, including its active transmissions."""
        return sum(
            len(bytes.fromhex(m.payload_hex))
            for key, m in messages.items()
            if status[key] == "retained" and owner[key] == node
        )

    def event(tick: int, key: int, node: int, kind: str) -> None:
        """Append a fixed semantic transition to the independent chronological ledger."""
        events.append({"tick": tick, "id": key, "node": node, "kind": kind})

    for tick in range(case.horizon):
        if tick == case.restart_tick and tick != 0:
            event(tick, 0, 0, "restart")
        for key, m in messages.items():
            if status[key] == "retained" and tick >= m.release + m.ttl:
                status[key] = "expired"
                busy[key] = False
                event(tick, key, owner[key], "expired")
        for key, m in messages.items():
            if status[key] == "unreleased" and m.release == tick:
                admitted = used(0) + len(bytes.fromhex(m.payload_hex)) <= capacity
                status[key] = "retained" if admitted else "rejected"
                event(tick, key, 0, "queued" if admitted else "source-rejected")
        arrivals = [f for f in flights if f["due"] == tick]
        flights = [f for f in flights if f["due"] != tick]
        for flight in arrivals:
            key, hop = flight["id"], flight["hop"]
            if flight["duplicate"] or owner[key] > hop:
                event(tick, key, hop + 1, "duplicate-suppressed")
                continue
            if status[key] != "retained":
                event(tick, key, hop + 1, "stale-arrival")
                continue
            busy[key] = False
            original = bytes.fromhex(messages[key].payload_hex)
            received = bytes([original[0] ^ 1]) + original[1:] if flight["corrupt"] else original
            if crc32c(received) != crc32c(original):
                kind = "integrity-rejected"
            elif hop == 0 and used(1) + len(original) > capacity:
                kind = "receiver-full"
            else:
                owner[key] = hop + 1
                if hop == 1:
                    status[key] = "delivered"
                    delivered[key] = tick
                    kind = "delivered"
                else:
                    kind = "relayed"
            event(tick, key, hop + 1, kind)
        for hop in (0, 1):
            contact = any(c.hop == hop and c.start <= tick < c.end for c in case.contacts)
            if not contact:
                continue
            ready = [
                m
                for key, m in messages.items()
                if status[key] == "retained" and owner[key] == hop and not busy[key]
            ]
            if not ready:
                continue
            message = min(
                ready, key=lambda m: (m.release if policy == 0 else m.release + m.ttl, m.id)
            )
            key = message.id
            busy[key] = True
            attempts[key][hop] += 1
            first = key == case.messages[0].id and hop == 0 and attempts[key][0] == 1
            flights.append(
                {
                    "id": key,
                    "hop": hop,
                    "due": tick + delay,
                    "corrupt": case.fault == 1 and first,
                    "duplicate": False,
                }
            )
            if case.fault == 2 and first:
                flights.append(
                    {
                        "id": key,
                        "hop": hop,
                        "due": tick + delay + 1,
                        "corrupt": False,
                        "duplicate": True,
                    }
                )
            event(tick, key, hop, "sent")
        samples.append(
            {
                "tick": tick,
                "probe_bytes": used(0),
                "relay_bytes": used(1),
                "inflight": len(flights),
                "delivered": sum(s == "delivered" for s in status.values()),
                "expired": sum(s == "expired" for s in status.values()),
                "rejected": sum(s == "rejected" for s in status.values()),
            }
        )
    output = [
        {
            "id": key,
            "status": status[key],
            "node": owner[key],
            "attempts": sum(attempts[key]),
            "delivered_tick": delivered[key],
            "crc32c": f"{crc32c(bytes.fromhex(message.payload_hex)):08x}",
        }
        for key, message in messages.items()
    ]
    return {"events": events, "samples": samples, "messages": output}
