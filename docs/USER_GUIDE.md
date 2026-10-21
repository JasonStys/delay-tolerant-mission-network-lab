# User guide

Author: Jason Stys. Help: [project issues](https://github.com/JasonStys/delay-tolerant-mission-network-lab/issues), [author profile](https://github.com/JasonStys).

## First experiment

Launch the portable executable or source service described in [README](../README.md). Your normal browser opens a loopback URL. This is the desktop app's interface, not a cloud account. The service console must remain running; Ctrl+C closes it.

1. Leave **Intermittent relay** selected. Wait for “Verified: Rust and Python traces agree.”
2. Use next/previous or the tick slider. Samples are post-tick values. The highlighted contact cursor is a simulated tick, not wall-clock time.
3. Compare source/relay retained bytes with the ground's cumulative accepted count. Sending does not release the sender's original until acceptance.
4. Expand the exact contact table; its end is excluded for departure. Arrival may occur after closure.
5. Inspect the message table at the selected tick. The ledger beneath it intentionally shows the complete run; filter one ID to follow it. Downloads always remain complete, not filtered.

Selectors automatically recompute; **Run experiment** repeats the current case. A failed native/reference check hides stale evidence and offers Retry. The app never displays a reference-only substitute. Optional **Remember settings** stores only finite selectors in localStorage; it is off by default and unchecking removes them. No run history/payload storage occurs automatically.

## Cases worth comparing

| Case                          | What to inspect                                                                                                                                   |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Intermittent relay            | Messages wait across closed windows and remain owned during flight                                                                                |
| Queue and backpressure        | At capacity 8/16, admission rejections and actual receiver-full events; compare capacity 32                                                       |
| Expiry before arrival         | Delay 3 makes ground arrival exactly at TTL; expiry wins                                                                                          |
| Corruption and retry          | `integrity-rejected` and subsequent original-owner retries                                                                                        |
| Duplicate copy suppression    | Extra copy arrivals never allocate a second owner/delivery                                                                                        |
| Restart with in-flight data   | A fresh Rust process resumes checkpoint state before tick 2, with copies actually in flight at every selectable delay; report includes its digest |
| FIFO versus earliest deadline | Default delay 3: compare policy 0/1; the one ground opportunity benefits different messages                                                       |
| No contact / retained data    | Zero deliveries is a valid result, not a failure; data can remain retained                                                                        |
| Empty network                 | No messages/contacts, stable zeros and no fabricated latency                                                                                      |

Mean latency is conditional on delivery. Always compare expired/rejected/retained totals before declaring a policy better. A final retained message may still have an in-flight copy. Capacity measures payload bytes, not real packet buffer overhead.

## Custom cases and disk evidence

Copy the example to a **new file** and edit only the strict [API](API.md) fields. Use the CLI `export --input ... --output ...`. Restart cases can add `--checkpoint-store checkpoints.sqlite3`; the actual stored handoff is reopened and supplied to the new worker. Add `--history history.sqlite3` for immutable complete reports. Both databases are plain unencrypted local files; neither is sent to GitHub or the browser. They cap at 100 distinct entries and do not delete old data for you. The checkpoint path is not an arbitrary saved-session resume command or power-loss demonstration.

Use `--format html` for a static readable complete report, `json` for full machine-readable evidence, `csv` for numeric queue samples, and `input` for the normalized case. Create parent folders first. Existing output files are never overwritten, even on repeated identical runs.

## Troubleshooting

- **Native worker missing:** source builds require `cargo build --release --locked`; portable apps must retain their whole extracted `_internal` tree.
- **UI missing:** source builds require `npm run build`. Do not serve the source HTML with a different web server; the UI requires the Python API.
- **Could not verify simulation:** retry once, then run the tests and report the case/settings/error. Do not treat hidden stale data as current evidence.
- **Port busy:** use the default ephemeral port or a different explicit `--port`; do not stop unrelated services.
- **OS warns about unsigned executable:** do not bypass protections. Inspect/build source or use an environment where policy permits verified unsigned lab programs.
- **Database full:** retain your evidence and choose a new path. No automated cleanup is performed.
- **Cannot complete operation:** confirm the schema and that the output does not exist. Unicode, unknown fields, duplicate keys, overlapping contacts and out-of-range values are errors by design.

No live network integration, flight decisions, authentication accounts or operational reliability guarantees are provided. Read [model limits](MODEL.md) before interpreting results.
