# Validation evidence

Author: Jason Stys. Initial source validation: 2026-10-20 local / 2026-10-21 UTC. Counts are executed tests, not claims that every possible defect is excluded. Release-specific workflow URLs and downloaded asset digests are recorded in release notes.

## Executed local checks

| Check                                                | Result                                                                                                                                                                               |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Rust formatting, Clippy `-D warnings`, release build | Passed, pinned 1.98.1; unsafe forbidden; zero external crates                                                                                                                        |
| Rust tests                                           | 5 passed: numeric CRC vectors, hand-derived boundaries, every 31 restart cuts plus per-byte checkpoint bit flips, malformed/case mismatch, 1,025 seeded hostile checkpoint envelopes |
| Python                                               | 300 passed on Windows/Python 3.14.6; 99.70% branch-inclusive coverage of `dtnlab` (495 statements, 174 branches); enforced minimum 90%                                               |
| TypeScript unit tests                                | 12 passed; strict compilation and production build passed                                                                                                                            |
| Browser integration                                  | 24 passed, 8 each in Chromium/Firefox/WebKit; real Python service and Rust worker, no trace screenshots/artifacts uploaded                                                           |
| Static source/docs                                   | Ruff, strict mypy, Prettier and exact-line/file inventory gates                                                                                                                      |
| Deterministic evidence                               | Nine default scenario contracts in [benchmark.json](reports/benchmark.json); all finite 162 UI configurations checked natively against independent Python                            |

Browser checks include actual replay without future-state leakage, observable fault/restart outcomes, policy/backpressure differences, all download formats, filtering, optional preference removal, failure/retry without stale evidence, inert hostile text, mobile-width keyboard controls and automated accessibility checks. Manual browser inspection and screenshots supplement—not replace—the assertions.

Python tests exercise strict schema/range/coercion/duplicate-key/Unicode/size handling, no-contact/empty cases, exact TTL/contact boundaries, deterministic property-generated cases, native failure/timeout/malformed output, SQLite immutability/hash/capacity, safe no-overwrite exports, exact Host/origin/Fetch Metadata, traversal/symlink controls and disconnect handling. Rust tests additionally reject malformed checkpoint states. No sanitizer, native coverage percentage, libFuzzer campaign or formal proof is claimed.

## Findings fixed during development

- A very large malformed-byte parameter's auto-generated pytest ID exceeded a practical Windows runner setup path. Explicit short test IDs fixed the harness; the oversized payload and assertions were retained.
- Rapid browser setting changes correctly canceled superseded fetches but exposed a handler attempting a second error response on a disconnected socket. Response headers/body writes now catch connection errors once. Two targeted header/body disconnect regression cases passed; real worker/data exceptions still fail.
- Rust Clippy requested bounded chunk APIs; code was updated rather than disabling the lint. A local Windows incremental-cache hardlink fallback only copied compiler intermediates and was not treated as a runtime correctness failure or reason to weaken OS protections.
- Manual semantic review found the originally chosen named restart cut could occur between flights. The fixture now checkpoints before tick 2; three delay-specific regressions require actual in-flight copies at that boundary. General every-boundary restart tests remain in place.
- A later local test invocation omitted the task's writable TEMP directory, so Windows sandbox fixture setup failed before affected tests ran. Re-running with a task-owned TEMP/TMP directory passed all 300 tests at the same coverage gate. No test assertions or filesystem protections were disabled. Hosted CI uses its normal runner temporary directory.

## Evidence interpretation

Every displayed/exported run requires exact native/reference trace agreement, including restart results. Both models can still share a specification mistake, so hand-derived outcomes, published CRC vectors, invariants, boundary cases and typed UI tests provide additional independent checks. Fault injection is deterministic and explicitly labeled, not production traffic evidence. Timing output includes subprocess/verification/tracing overhead and reports **Python traced allocation peak**, not Rust RSS or a hard real-time budget. Run `python -m tools.benchmark` to reproduce contracts and observe your machine's descriptive timings.

The GitHub workflow additionally repeats model checks on Linux Python 3.12/3.14, Windows/macOS Python 3.14; runs dependency audits and CodeQL (Python/TypeScript); and executes portable apps on three OSes. Results must actually pass before publication; see [release runbook](RELEASE.md). Platform runner success does not imply every OS release/architecture is supported.

## Unvalidated / deliberately out of scope

BPv7 interoperability, BPSec, real radios/contact geometry, malicious peer identity, ACK loss, distributed exactly-once semantics, power loss or crash-during-write durability, radiation/hardware faults, operational spacecraft use, public multiuser hosting, unsigned-binary trust and mobile installers. No Docker repair, external service setup or user-data ingestion was performed.
