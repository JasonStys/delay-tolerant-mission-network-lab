# Input, worker and HTTP contracts

Author: Jason Stys. Interfaces are lab-specific schema version 1, not standardized mission protocols.

## Local input JSON

Start with [examples/restart.json](../examples/restart.json), exported by the application itself. CLI imports read at most 65,536 bytes plus one over-limit sentinel. Malformed UTF-8, duplicate object keys, unexpected/missing fields, excessive nesting and coercions are rejected. Integer fields reject booleans/floats/strings. No input field can select an executable, URL or output path.

| Field          | Exact constraints                                                                                                              |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `schema`       | Integer 1                                                                                                                      |
| `name`         | 1–48 lower-case alphanumeric/hyphen characters; first alphanumeric                                                             |
| `horizon`      | Integer 1–64                                                                                                                   |
| `restart_tick` | 0 disables; otherwise 1 through horizon−1                                                                                      |
| `fault`        | 0 none; 1 corrupt the lowest-ID message's first source-hop send; 2 add a duplicate to that send only                           |
| `messages`     | JSON list of ≤32 exact objects: `id` unique 1–32, `release` 0 through horizon−1, `ttl` 1–64, `payload_hex` 1–16 full hex bytes |
| `contacts`     | JSON list of ≤32 exact objects: `hop` 0/1, `start` 0 through horizon−1, `end` start+1 through horizon; no same-hop overlap     |

Messages normalize by ID; contacts by hop/start/end; hex normalizes to lower case. Empty lists and zero-delivery cases are valid. Fixed CLI controls are capacity 8/16/32, delay 1/3/5, policy 0/1. `--scenario` records selected settings even for imported cases, but imported `name`, contacts and messages govern the experiment; provenance explicitly says unverified local synthetic input.

## Worker boundary

The fixed source or bundled `network-core` executable accepts at most 16 KiB stdin. The `DTN1` header supplies horizon/capacity/delay/policy/fault/pause. `M` rows carry message ID/release/TTL/hex; `C` rows carry hop/start/end. Optional `S` carries checkpoint hex. Parsing must finish before stdout. Invalid input exits 2 with a constant diagnostic. No CLI path arguments, shell, filesystem or networking are exposed by this protocol.

Python enforces a five-second subprocess timeout, a 1 MiB output check and exact envelope keys: `events`, `samples`, `messages`, `checkpoint`; bounded list/object shapes; checkpoint string length ≤2,048. Actual result traces must also equal the independent reference or the run fails. Output is captured before the size check; the trusted worker's bounded model, not a streaming untrusted-child quota, is the primary output bound. See [MODEL](MODEL.md) for state semantics and checkpoint limits.

## Read-only loopback HTTP

The server binds **only `127.0.0.1`**, not all interfaces. No accounts, writes, imports, uploads, remote fetches or public hosting endpoints exist.

| Route                                                | Result                                          |
| ---------------------------------------------------- | ----------------------------------------------- |
| `/` and confined built asset paths                   | Production UI/asset bytes                       |
| `/api/health`                                        | Fixed local mode/status JSON                    |
| `/api/catalog`                                       | Built-in scenarios, finite choices/defaults     |
| `/api/run?scenario=...&capacity=16&delay=3&policy=0` | Complete independently verified report          |
| `/api/report?...&format=json`                        | Fixed-name download: JSON, CSV, HTML or `input` |

Unknown/duplicate query fields, invalid values, oversized request targets (>1 KiB) and >8 fields are rejected. Host must exactly match the loopback listener and port. Origin, when supplied, must match; cross-site Fetch Metadata is rejected. No CORS access is granted. Only read operations are supported. Invalid requests return generic errors; native/data failures never return fabricated successes. Client disconnects abandon the response without a second write.

Reports include schema, name, normalized input/settings, provenance/limitations, totals, complete events/samples/messages and recovery metadata. `id` is SHA-256 of canonical sorted-key indented ASCII JSON excluding the `id` itself, with a final newline and no NaN/infinity. Timing, machine paths and secrets do not enter identity. Import provenance and SQLite recovery mode legitimately change report identity.

JSON and HTML contain the full report. CSV intentionally contains only numeric post-tick queue/cumulative outcome samples, **not** full events or payloads. `input` downloads only normalized input. HTML escapes the report and has no scripts or external resources. All file exports refuse overwriting existing destinations.

## SQL evidence

`--history` inserts verified report JSON under its content hash. `--checkpoint-store` only works on restart cases and stores wire/checkpoint under a combined SHA-256. Both use parameterized SQL, immediate transactions, idempotent same-key insertion, immutable update/delete triggers and 100-entry limits. No automatic pruning or public read endpoint exists. SQL triggers are application safeguards, not protection from a local filesystem owner who can replace the database. Choose user-owned local paths and keep sensitive information out of test payloads.
