# Architecture and decisions

Author: Jason Stys. Scope: bounded offline distributed-systems education, not operational mission communications.

## Data flow and trust boundaries

```text
Browser finite selectors -> read-only loopback Python service
CLI explicit bounded JSON -> strict Case schema
                      -> fixed Rust executable, finite stdin envelope
                      -> independent Python dictionary/CRC replay
                      -> compare full events + samples + messages
                      -> deterministic report, optional CLI SQLite/export
```

Only the local CLI accepts file paths. Neither the browser nor payloads select a process, URL, shell, filesystem target, or network destination. The worker has no network or file APIs; it reads bounded stdin and emits JSON stdout. Payload bytes are opaque, not decoded into commands or HTML. A missing or failed native worker is an error, not an invitation to display reference-only results.

## Decisions and trade-offs

| Decision                               | Reason                                                                            | Cost / limit                                                                                    |
| -------------------------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Dependency-free safe Rust core         | Explicit ownership, bounded arithmetic, memory safety, portable small worker      | Additional compiler for source builds; no Rust coverage or formal-verification claim            |
| Independently structured Python oracle | Catch cross-language algorithm/serialization/restart drift on every displayed run | Roughly doubles simulation work; shared specification errors remain possible                    |
| Finite three-node, two-hop topology    | Reviewable reproducible state space; focus on queue/restart behavior              | Not general routing, congestion control, real bandwidth, or BP interoperability                 |
| TypeScript + native browser SVG        | Typed UI, portable local browser, exact numeric table alternative                 | Requires a local desktop service; not an installable mobile app                                 |
| One-directory frozen desktop bundles   | One executable starts without package-manager commands                            | Unsigned OS/architecture-specific downloads; not universal binaries                             |
| CLI-only immutable SQL evidence        | Deliberate local writes, stable content identities and disk-handoff demonstration | No encryption, multiuser accounts, remote synchronization, or arbitrary saved-session resume UI |
| Full trace plus canonical SHA-256      | Explainability and reproducibility across platforms                               | Hashes are not signatures; avoid real sensitive payloads                                        |

The Rust model uses explicit progress/flight records; Python uses independent dictionaries and table-driven CRC rather than importing Rust code. Rust's CRC is bit-oriented. Full agreement is required, not only equal summary totals. Unit tests also check hand-derived outcomes and published numeric CRC vectors so that two implementations agreeing is not the sole correctness argument.

## State and restart

A message is unreleased, retained at source/relay, delivered, expired, or source-rejected. A busy retained message has exactly one original in-flight copy; an injected duplicate is a non-authoritative extra arrival. Sender ownership remains until acceptance. At a restart boundary, the first worker exits; state bytes are checked and restored by a new subprocess. Python retains prefix evidence and combines the resumed trace. Optional SQLite handoff commits, closes, reopens, and hash-checks the bytes first. This is not a power-failure transaction protocol. See [MODEL](MODEL.md).

## Bounds and complexity

Let H be ticks (≤64), M messages (≤32), C contacts (≤32), F the maximum live flight-record count. The simulator scans messages/contacts/flights and sorts eligible messages per hop. Capacity checks themselves scan M records: admitting up to M releases and processing up to F arrivals gives a **conservative, not tight**, O(H × (M² + FM + M log M + C + F)) time bound. The fixed two-hop, fixed-delay model greatly restricts simultaneous arrivals; this bound intentionally does not assume that optimization. Retained trace evidence has a conservative O(HM + HF) space bound. Original in-flight copies are bounded by M and there is at most one injected extra duplicate globally. Core state is O(M + C + F). These are source-analysis upper bounds, not a measured Big-O experiment or real-time deadline proof.

The reference's CRC lookup table is cached once, and report latency lookup uses an ID map rather than a repeated linear search. Bounded work makes the independent checker practical without premature general-purpose infrastructure. Worker execution has a five-second subprocess deadline. Input/output/row limits are defensive bounds around trusted local code, not a hostile shared-server resource quota: concurrent local clients can still consume CPU and threads.

## Failure handling

Strict import errors produce controlled CLI errors; unknown HTTP query fields and cross-origin/Host failures are rejected. Native/reference mismatch withholds evidence. Browser request supersession aborts fetches and hides stale output. Client disconnects are handled once without trying to write a second response; actual worker/data errors are still errors. No runtime telemetry, external fonts, analytics, remote scripts, or ads are included. Source and executable are trusted local components: OS compromise can replace them and defeats these controls.

Future operational work would require an actual standardized protocol stack, authenticated peers, ACK-loss/retransmission semantics, topology routing, link/clock models, adversarial deployment controls, and independent mission assurance. It must not be inferred from this lab's success.
