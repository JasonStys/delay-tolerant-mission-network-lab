"""Native/reference, conservation and restart verification by Jason Stys.

Functions: test_* contracts. Variables: finite settings product, independent vectors and valid random cases.
Exact definition/variable locations: docs/CODE_INDEX.md. Real Rust execution is required throughout.
"""

import itertools
import sqlite3
from contextlib import closing
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import settings as hypothesis_settings
from hypothesis import strategies as st

from dtnlab.engine import (
    CHOICES,
    SCENARIOS,
    Settings,
    analyze,
    build_run,
    canonical,
    fixture,
    run_id,
)
from dtnlab.model import Contact, Message
from dtnlab.native import invoke, persist_checkpoint
from dtnlab.reference import crc32c


@pytest.mark.parametrize(
    "scenario,capacity,delay,policy", list(itertools.product(SCENARIOS, *CHOICES.values()))
)
def test_grid(scenario, capacity, delay, policy):
    """All 162 finite configurations agree cross-language and conserve terminal/retained message counts."""
    config = Settings(scenario, capacity, delay, policy)
    run = build_run(config)
    assert run["id"] == run_id(run)
    assert canonical(run) == canonical(build_run(config))
    total = run["totals"]
    assert total["offered"] == sum(
        total[key] for key in ("delivered", "expired", "rejected", "retained", "unreleased")
    )
    assert len(run["samples"]) == run["input"]["horizon"]
    for sample in run["samples"]:
        assert sample["probe_bytes"] <= capacity and sample["relay_bytes"] <= capacity
        assert sample["delivered"] + sample["expired"] + sample["rejected"] <= total["offered"]
    assert len([e for e in run["events"] if e["kind"] == "delivered"]) == total["delivered"]


def test_manual_handoff_expiry_and_policy():
    """Hand-derived departure/arrival times, exact expiry boundary and ordering outcomes are distinct."""
    case = replace(
        fixture("empty-network"),
        horizon=8,
        messages=(Message(1, 0, 7, "aabb"),),
        contacts=(Contact(0, 0, 2), Contact(1, 2, 3)),
    )
    run = analyze(case, Settings(delay=1))
    assert [(e["tick"], e["kind"]) for e in run["events"]] == [
        (0, "queued"),
        (0, "sent"),
        (1, "relayed"),
        (2, "sent"),
        (3, "delivered"),
    ]
    assert run["samples"][0]["probe_bytes"] == 2 and run["samples"][1]["relay_bytes"] == 2
    expired = analyze(replace(case, messages=(Message(1, 0, 3, "aabb"),)), Settings(delay=1))
    assert expired["totals"]["expired"] == 1 and expired["totals"]["delivered"] == 0
    assert any(e["kind"] == "stale-arrival" and e["tick"] == 3 for e in expired["events"])
    fifo = build_run(Settings("priority-choice", policy=0))
    edf = build_run(Settings("priority-choice", policy=1))
    assert [m["id"] for m in fifo["messages"] if m["status"] == "delivered"] == [1]
    assert [m["id"] for m in edf["messages"] if m["status"] == "delivered"] == [2]


def test_faults_backpressure_and_retention():
    """Corrupt retry, duplicate suppression, receiver-full retries and disconnected retention are observable."""
    corrupt = build_run(Settings("corrupt-first"))
    assert corrupt["totals"]["integrity_rejected"] == 1 and corrupt["totals"]["attempts"] == 7
    duplicate = build_run(Settings("duplicate-copy"))
    assert duplicate["totals"]["duplicates"] == 1 and duplicate["totals"]["delivered"] == 3
    pressure = build_run(Settings("queue-pressure", capacity=8))
    assert pressure["totals"]["receiver_full"] > 0 and pressure["totals"]["rejected"] > 0
    disconnected = build_run(Settings("no-contact"))
    assert disconnected["totals"]["retained"] == 3 and disconnected["totals"]["attempts"] == 0


@pytest.mark.parametrize("fault,kind", [(1, "integrity-rejected"), (2, "duplicate-suppressed")])
def test_fault_targets_lowest_id_not_first_departure(fault, kind):
    """Only the lowest-ID message's first source send is injected, or none if it is never admitted."""
    case = replace(
        fixture("empty-network"),
        fault=fault,
        messages=(Message(1, 4, 28, "aabb"), Message(2, 0, 32, "1122")),
        contacts=(Contact(0, 0, 32), Contact(1, 0, 32)),
    )
    result = analyze(case, Settings())
    assert [event["id"] for event in result["events"] if event["kind"] == kind] == [1]
    assert [event["id"] for event in result["events"] if event["kind"] == "sent"][0] == 2
    rejected = replace(case, messages=(Message(1, 4, 28, "ab" * 16), case.messages[1]))
    result = analyze(rejected, Settings(capacity=8))
    assert result["messages"][0]["status"] == "rejected"
    assert not any(event["kind"] == kind for event in result["events"])


@pytest.mark.parametrize("cut", range(1, 32))
def test_fresh_process_every_boundary(cut):
    """Two actual worker subprocesses resume identical outcomes/events at every supported boundary."""
    case = replace(fixture("duplicate-copy"), restart_tick=cut)
    resumed = analyze(case, Settings())
    full = build_run(Settings("duplicate-copy"))
    assert resumed["messages"] == full["messages"] and resumed["samples"] == full["samples"]
    assert [e for e in resumed["events"] if e["kind"] != "restart"] == full["events"]
    assert resumed["recovery"]["next_tick"] == cut


def test_sqlite_restart_handoff(tmp_path):
    """Checkpoint is committed, read through a new connection and handed to a fresh native process."""
    path = tmp_path / "checkpoints.sqlite3"
    result = build_run(Settings("restart-inflight"), path)
    assert result["recovery"]["mode"] == "sqlite-and-fresh-worker"
    assert result["totals"]["delivered"] == 3
    # The named demonstration must actually stop with original/duplicate copies in flight.
    cut = result["recovery"]["next_tick"]
    assert result["samples"][cut - 1]["inflight"] > 0
    with closing(sqlite3.connect(path)) as database:
        assert database.execute("SELECT count(*) FROM checkpoints").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            database.execute("UPDATE checkpoints SET checkpoint='00'")
    again = build_run(Settings("restart-inflight"), path)
    assert canonical(again) == canonical(result)
    with pytest.raises(ValueError, match="requires a restart"):
        build_run(Settings(), path)


@pytest.mark.parametrize("delay", CHOICES["delay"])
def test_named_restart_has_inflight_copies(delay):
    """Every selectable delay leaves original/duplicate flight state at the named checkpoint cut."""
    result = build_run(Settings("restart-inflight", delay=delay))
    cut = result["recovery"]["next_tick"]
    assert cut == 2 and result["samples"][cut - 1]["inflight"] > 0


def test_checkpoint_store_capacity_and_tamper(tmp_path):
    """Immutable handoff storage refuses overflow or modified stored bytes; never auto-prunes."""
    path = tmp_path / "full.sqlite3"
    persist_checkpoint(path, "wire", "00")
    with closing(sqlite3.connect(path)) as database, database:
        database.executemany(
            "INSERT INTO checkpoints(id,wire,checkpoint) VALUES(?,?,?)",
            [(str(i).zfill(64), "seed", "00") for i in range(99)],
        )
    with pytest.raises(ValueError, match="store full"):
        persist_checkpoint(path, "different", "00")
    with closing(sqlite3.connect(path)) as database, database:
        database.execute("DROP TRIGGER checkpoints_no_update")
        database.execute("UPDATE checkpoints SET checkpoint='01' WHERE wire='wire'")
    with pytest.raises(ValueError, match="hash mismatch"):
        persist_checkpoint(path, "wire", "00")


def test_reference_disagreement_withholds(monkeypatch):
    """An independently detected mismatch is a failure, not a substitute successful result."""
    monkeypatch.setattr("dtnlab.engine.simulate", lambda *args: {"messages": []})
    with pytest.raises(RuntimeError, match="disagreement"):
        build_run()


@pytest.mark.parametrize(
    "key,value",
    [
        ("scenario", "unknown"),
        ("scenario", []),
        ("capacity", True),
        ("capacity", 16.0),
        ("delay", 2),
        ("policy", False),
    ],
)
def test_invalid_settings(key, value):
    """Unsupported finite settings are not coerced into valid controls."""
    with pytest.raises(ValueError):
        Settings(**{key: value})


def test_known_crc_vectors():
    """RFC 3720 byte examples interpreted as reflected numeric CRC-32C values match independently."""
    assert crc32c(bytes(32)) == 0x8A9136AA
    assert crc32c(bytes([255]) * 32) == 0x62A8AB43
    assert crc32c(bytes(range(32))) == 0x46DD794E
    assert crc32c(bytes(reversed(range(32)))) == 0x113FDB5C


@hypothesis_settings(max_examples=100, derandomize=True, deadline=None)
@given(
    st.lists(
        st.tuples(st.integers(0, 15), st.integers(1, 32), st.binary(min_size=1, max_size=16)),
        max_size=12,
    ),
    st.sampled_from([8, 16, 32]),
    st.sampled_from([1, 3, 5]),
    st.integers(0, 1),
    st.integers(0, 2),
    st.integers(0, 31),
)
def test_generated_networks(records, capacity, delay, policy, fault, restart):
    """100 generated valid networks compare full native/reference traces, CRCs and restart boundaries."""
    messages = tuple(
        Message(index + 1, release, ttl, payload.hex())
        for index, (release, ttl, payload) in enumerate(records)
    )
    case = replace(
        fixture("intermittent-relay"), messages=messages, fault=fault, restart_tick=restart
    )
    result = analyze(case, Settings(capacity=capacity, delay=delay, policy=policy))
    assert result["totals"]["offered"] == len(records)


@pytest.mark.parametrize(
    "wire",
    [
        "",
        "DTN1 0 8 1 0 0 0\n",
        "DTN1 32 8 1 0 0 0\nS aa\n",
        "DTN1 32 8 1 0 0 0\nM 1 0 3 zz\n",
        "DTN1 32 8 1 0 0 0\nC 0 1 4\nC 0 3 5\n",
        "x" * 16385,
    ],
    ids=["empty", "horizon", "checkpoint", "hex", "overlap", "oversized-input"],
)
def test_native_invalid_envelope(wire):
    """Malformed native inputs/checkpoints fail without partial JSON evidence."""
    with pytest.raises((ValueError, RuntimeError)):
        invoke(wire)
