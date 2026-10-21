# Network model and exact semantics

Author: Jason Stys. Every message, contact, tick and failure is invented; units are dimensionless simulated ticks and retained payload bytes.

## Topology and controls

Probe (node 0) → Relay (node 1) → Ground application sink (node 2). Hop 0 is Probe→Relay; hop 1 is Relay→Ground. No reverse links, routing choices, fragmentation, radio measurements or real traffic exist. Ground acceptance is terminal and not constrained by the source/relay retention capacity. Capacity 8/16/32 counts each source/relay's original payload bytes, including originals whose copies are in flight; it is not packet overhead, disk usage, or process RSS.

Each open hop may start **one complete message per tick**, regardless of its size. A departure is allowed when `start <= tick < end`. Arrival is at departure + selected delay (1/3/5 ticks), even after that contact closes. Runs process ticks 0 through horizon−1; arrivals beyond the horizon do not magically deliver. In-flight copies and retained messages can remain at the end.

Source-order FIFO sorts eligible messages by their source release tick, then ID. It is not relay-arrival FIFO. Earliest expiry sorts by absolute release+TTL, then ID. Neither is claimed optimal. A message's lifetime starts at source release, not each hop. Non-overlapping same-hop windows may be adjacent.

## Tick phases (order matters)

1. Expire retained messages where tick ≥ release+TTL. This happens **before arrivals** at that tick; an arrival exactly at expiry is not delivered.
2. Admit this tick's releases in sorted ID order. Reject a new message if source capacity is insufficient; never silently evict retained data. This happens before arrivals free sender bytes in the same tick.
3. Process due flights in stable insertion order. A non-authoritative injected duplicate or copy of already-advanced progress is suppressed. A copy whose message is already terminal is stale. For an original retained flight, clear its busy flag, apply any injected corruption and compare its CRC against the trusted original. A bad CRC or full relay refuses transfer; the sender retains ownership and can retry. Acceptance atomically advances the logical owner; ground acceptance marks delivery.
4. On each open hop, choose and send one eligible, nonbusy retained message. Retain its original at the sender until accepted. A refused transfer can retry at this tick if a contact is open.
5. Record post-tick source/relay bytes, count of flight copies and cumulative terminal outcomes.

These phase semantics deliberately make boundary cases deterministic. The browser's replay state is reconstructed only from events up to its selected tick; the ledger and metrics are explicitly full-run evidence.

## Faults and guarantees not claimed

- Fault 0: none.
- Fault 1: the lowest-ID message's first source-hop send has its first payload byte flipped at arrival. CRC-32C rejects it, the sender keeps the trusted original, and retries if possible. Other messages and later sends are unaffected; if that message is never sent, no fault is injected.
- Fault 2: the lowest-ID message's first source-hop send also schedules one duplicate copy, due one tick after the original. The duplicate is marked non-authoritative and never takes ownership. Other messages and later sends are unaffected. This demonstrates explicit duplicate handling, **not adversarial duplicate identification or ACK-loss exactly-once delivery**.

The single global state machine supplies instantaneous abstract acceptance acknowledgments. It does not model dropped ACKs, distributed consensus, independent node crashes, mutable external clock state, endpoint authentication or malicious payload rewriting. CRC-32C and SHA-256 evidence identities detect accidental changes under the stated checks; neither authenticates a sender. A malicious editor can recompute them.

Mean delivery latency uses **delivered messages only**. Interpret it alongside offered, expired, rejected and retained totals; a low latency does not imply high success. Flight counts include injected/stale copies until their due processing and do not imply unique retained messages.

## Checkpoint

The boundary is **before** `restart_tick` phases; zero disables restart. A DNC1 checkpoint contains a case fingerprint, next tick, progress rows and in-flight copies, followed by CRC-32C. It is little-endian, versioned and limited to 1,024 bytes. The case fingerprint excludes the pause control so the second worker can resume the same case without pausing again. Restore rejects malformed version/length/checksum/case binding, invalid state/boolean/range/counts, capacity violations and mismatched busy/original-flight ownership. It is not a public stable interchange format.

The first process exits, then a fresh native process resumes. Python retains earlier samples/events outside the checkpoint and adds a restart marker. With `--checkpoint-store`, Python first commits wire/checkpoint text to SQLite, closes and reopens it, verifies its hash and feeds the stored bytes to the second process. This validates a persisted handoff at a completed phase boundary, **not** power loss, fsync durability, crash during a write or arbitrary process-death recovery. History reports are not resume commands.

## Standards context

[IETF RFC 9171](https://www.rfc-editor.org/rfc/rfc9171.html) describes the Bundle Protocol's store/carry/forward context and lifetime concepts. This lab does not implement its CBOR wire format, blocks, processing or convergence layers. [RFC 9172](https://www.rfc-editor.org/rfc/rfc9172.html) describes BPSec: CRC alone is not that security system. [RFC 3720 Appendix B.4](https://www.rfc-editor.org/rfc/rfc3720.html#appendix-B.4) supplies published CRC-32C test vectors. Numeric reflected values tested here are 0x8a9136aa for 32 zero bytes, 0x62a8ab43 for 32 FF bytes, 0x46dd794e for ascending 00..1F and 0x113fdb5c for descending 1F..00. Numeric values and transmitted little-endian byte order must not be confused. No RFC implementation/text was copied into the source.
