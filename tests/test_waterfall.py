"""Hand-calculated message latency and conservative bottleneck contracts by Jason Stys.

Functions: manual and test_*; variables: two-hop departure/arrival ticks, expiry and failure traces.
All integrations require the unchanged Rust/reference agreement. Lines: docs/CODE_INDEX.md.
"""

from copy import deepcopy
from dataclasses import replace

import pytest

from dtnlab.engine import SCENARIOS, Settings, analyze, build_run
from dtnlab.model import Case, Contact, Message
from dtnlab.reference import simulate
from dtnlab.waterfall import waterfalls


def manual(ttl: int = 20) -> Case:
    """A send at0, relay at3, relay-send at5 and delivery at8 has six flight/two queue ticks."""
    return Case(
        "manual", 12, 0, 0, (Message(1, 0, ttl, "aa"),), (Contact(0, 0, 2), Contact(1, 5, 8))
    )


def test_independent_two_hop_latency_and_ttl_boundary():
    """Half-open contact waits and expiration-before-arrival have manually known outcomes."""
    run = analyze(manual(), Settings())
    item = run["waterfalls"][0]
    assert (item["delivery_latency_ticks"], item["queue_ticks"], item["in_flight_ticks"]) == (
        8,
        2,
        6,
    )
    assert item["bottlenecks"]["no_contact_ticks"] == 2
    assert [(s["start"], s["end"], s["phase"]) for s in item["spans"]] == [
        (0, 3, "in-flight-hop-0"),
        (3, 5, "queue-no-contact-hop-1"),
        (5, 8, "in-flight-hop-1"),
        (8, 12, "delivered"),
    ]
    expired = analyze(manual(ttl=3), Settings())["waterfalls"][0]
    assert expired["status"] == "expired" and expired["delivery_latency_ticks"] is None
    assert expired["observed_elapsed_ticks"] == expired["in_flight_ticks"] == 3
    assert expired["bottlenecks"]["stale_arrivals"] == 1
    assert not expired["censored"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_every_fixture_accounts_for_elapsed_and_actual_events(scenario):
    """No-contact, corruption, duplicates, queue pressure and restart retain actual trace causes."""
    run = build_run(Settings(scenario=scenario, capacity=8))
    for item in run["waterfalls"]:
        assert item["queue_ticks"] + item["in_flight_ticks"] == item["observed_elapsed_ticks"]
        assert sum(s["end"] - s["start"] for s in item["spans"]) == run["input"]["horizon"]
        assert item["bottlenecks"]["receiver_full_events"] == sum(
            e["kind"] == "receiver-full" for e in item["events"]
        )
    if scenario == "empty-network":
        assert run["waterfalls"] == []
    elif scenario == "queue-pressure":
        assert any(i["bottlenecks"]["receiver_full_events"] for i in run["waterfalls"])
    elif scenario == "no-contact":
        assert any(i["censored"] and i["queue_ticks"] for i in run["waterfalls"])


def test_source_rejection_unreleased_ordering_and_bad_trace():
    """A rejected message has no delivery latency; future releases and truncated traces cannot fake it."""
    case = replace(
        manual(),
        messages=(Message(1, 0, 20, "aa" * 8), Message(2, 0, 20, "bb"), Message(3, 20, 2, "cc")),
    )
    trace = simulate(case, 8, 3, 0)
    rows = waterfalls(case, trace)
    assert rows[1]["status"] == "rejected" and rows[1]["observed_elapsed_ticks"] == 0
    assert rows[1]["bottlenecks"]["source_rejected_events"] == 1
    assert rows[2]["status"] == "unreleased" and rows[2]["censored"]
    malformed = deepcopy(trace)
    malformed["events"] = [e for e in malformed["events"] if e["kind"] != "queued"]
    with pytest.raises(RuntimeError, match="inconsistent"):
        waterfalls(case, malformed)


def test_open_contact_wait_is_ordering_not_missing_link():
    """Two ready messages cannot both depart on one hop at the same tick."""
    case = replace(
        manual(),
        messages=(Message(1, 0, 20, "aa"), Message(2, 0, 20, "bb")),
        contacts=(Contact(0, 0, 12), Contact(1, 0, 12)),
    )
    rows = analyze(case, Settings())["waterfalls"]
    assert rows[1]["bottlenecks"]["open_contact_not_selected_ticks"] == 1
    assert rows[1]["bottlenecks"]["no_contact_ticks"] == 0
