"""Per-message trace accounting by Jason Stys.

Function: waterfalls. Variables: message-local post-tick states, compressed half-open spans,
queue/contact observations and actual failure counters. Definition lines: docs/CODE_INDEX.md.
This explains verified lab events without changing the simulator or inventing radio causes.
"""

from collections import Counter
from typing import Any

from dtnlab.model import Case


def waterfalls(case: Case, trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive bounded full-run queue/hop spans; fail closed on inconsistent final accounting.

    Spans represent post-tick state on [start,end), not individual event timestamps. Terminal
    spans are excluded from latency. A queued message at an open contact was not selected that
    tick; this is ordering/one-send-per-hop pressure, not inferred packet loss or link bandwidth.
    """
    result = []
    final = {row["id"]: row for row in trace["messages"]}
    by_message: dict[int, list[dict[str, Any]]] = {message.id: [] for message in case.messages}
    for event in trace["events"]:
        if event["kind"] != "restart":
            by_message[event["id"]].append(event)
    for message in case.messages:
        events = by_message[message.id]
        by_tick: dict[int, list[dict[str, Any]]] = {}
        for event in events:
            by_tick.setdefault(event["tick"], []).append(event)
        status, node, busy = "unreleased", 0, False
        spans: list[dict[str, Any]] = []
        counts: Counter[str] = Counter()
        for tick in range(case.horizon):
            for event in by_tick.get(tick, []):
                kind = event["kind"]
                if kind == "queued":
                    status, node, busy = "retained", 0, False
                elif kind == "sent":
                    busy = True
                elif kind in {"integrity-rejected", "receiver-full"}:
                    busy = False
                elif kind == "relayed":
                    node, busy = 1, False
                elif kind in {"delivered", "expired", "source-rejected"}:
                    status = "rejected" if kind == "source-rejected" else kind
                    busy = False
                    if kind == "delivered":
                        node = 2
            if status == "retained":
                if busy:
                    phase = f"in-flight-hop-{node}"
                elif any(c.hop == node and c.start <= tick < c.end for c in case.contacts):
                    phase = f"queue-open-contact-hop-{node}"
                else:
                    phase = f"queue-no-contact-hop-{node}"
                counts[phase] += 1
            else:
                phase = status
            if spans and spans[-1]["phase"] == phase and spans[-1]["node"] == node:
                spans[-1]["end"] = tick + 1
            else:
                spans.append({"start": tick, "end": tick + 1, "phase": phase, "node": node})
        actual = final[message.id]
        terminal = next(
            (
                event["tick"]
                for event in events
                if event["kind"] in {"delivered", "expired", "source-rejected"}
            ),
            case.horizon,
        )
        elapsed = max(0, terminal - message.release)
        if status != actual["status"] or node != actual["node"] or sum(counts.values()) != elapsed:
            raise RuntimeError("Waterfall trace inconsistent with verified final accounting")
        kinds = Counter(event["kind"] for event in events)
        result.append(
            {
                "id": message.id,
                "release": message.release,
                "expires_at": message.release + message.ttl,
                "status": status,
                "observed_elapsed_ticks": elapsed,
                "delivery_latency_ticks": actual["delivered_tick"] - message.release
                if status == "delivered"
                else None,
                "first_send_tick": next(
                    (event["tick"] for event in events if event["kind"] == "sent"), None
                ),
                "queue_ticks": sum(
                    value for phase, value in counts.items() if phase.startswith("queue-")
                ),
                "in_flight_ticks": sum(
                    value for phase, value in counts.items() if phase.startswith("in-flight-")
                ),
                "phase_ticks": dict(sorted(counts.items())),
                "spans": spans,
                "events": events,
                "bottlenecks": {
                    "no_contact_ticks": sum(
                        value
                        for phase, value in counts.items()
                        if phase.startswith("queue-no-contact")
                    ),
                    "open_contact_not_selected_ticks": sum(
                        value
                        for phase, value in counts.items()
                        if phase.startswith("queue-open-contact")
                    ),
                    "receiver_full_events": kinds["receiver-full"],
                    "integrity_rejected_events": kinds["integrity-rejected"],
                    "source_rejected_events": kinds["source-rejected"],
                    "stale_arrivals": kinds["stale-arrival"],
                    "duplicate_suppressed_events": kinds["duplicate-suppressed"],
                },
                "censored": status in {"retained", "unreleased"},
            }
        )
    return result
