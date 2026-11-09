# Explain each message's latency

The complete-run waterfall expands each message into compressed half-open spans of **post-tick state**: unreleased, waiting for a hop with no contact, waiting at an open contact, in flight on hop0/1, delivered, expired or source rejected. The panel is explicitly independent of the replay cursor and can show future outcomes relative to that cursor. The original tick-replay table remains causal.

Queue ticks plus flight ticks equal the observed time from release until delivery, expiry or the experiment end. Terminal spans are excluded. Delivered-only end-to-end latency remains null for other outcomes. A retained or unreleased message at the window end is **censored**, not a successful delivery or a known eventual failure. TTL expires at `release + ttl`, before arrivals at that same tick; a later stale arrival cannot rescue an expired message.

Counts explain actual observed causes: no-contact ticks, open-contact ticks when that message was not selected, receiver-full rejections, integrity rejections, source admission rejection, duplicate suppression and stale arrivals. Open-contact waiting reflects ordering and the one-whole-message-per-hop-per-tick rule. Retained capacity counts bytes, not link bandwidth. These explanations do not infer RF interference, real packet loss, malicious behavior or physical route quality.

Native Rust events, samples and final states still must agree with the independent Python simulation before any report is published. Waterfall accounting additionally fails closed on mismatched final state or elapsed-time conservation. The same ledger is included in JSON/HTML CLI exports and immutable history under the run hash. No radios, real mission connections or arbitrary network destinations exist.
