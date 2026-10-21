/** Deterministic network replay interface by Jason Stys.
 * Functions: controls, load, render, replay, ledger. State: settings, report, controller, tick, messageFilter.
 * Exact lines: docs/CODE_INDEX.md. No live traffic, arbitrary input paths or HTML payload execution.
 */
import {
  bounded,
  choices,
  defaults,
  display,
  escape,
  isReport,
  parsePreferences,
  replayMessages,
  scenarios,
  timelineSvg,
  type Report,
  type Settings,
} from "./contracts";
import "./style.css";
const app = document.querySelector<HTMLDivElement>("#app")!;
const storageKey = "mission-network-preferences-v1";
let settings = { ...defaults },
  remember = false;
try {
  const saved = parsePreferences(localStorage.getItem(storageKey));
  if (saved) {
    settings = saved;
    remember = true;
  }
} catch {
  /* Preferences are optional, never required for simulation. */
}
let report: Report | null = null;
let controller: AbortController | null = null;
let tick = 0;
let messageFilter = "all";
app.innerHTML = `<header class="top"><a class="brand" href="#workspace"><span aria-hidden="true">◈</span> LINKSTATE <small>/ MISSION NETWORK LAB</small></a><nav aria-label="Project"><a href="#guide">How it works</a><a href="https://github.com/JasonStys/delay-tolerant-mission-network-lab" rel="noreferrer">Source ↗</a><a href="https://github.com/JasonStys" rel="noreferrer">Jason Stys ↗</a></nav></header><main id="workspace"><section class="hero"><div><p class="eyebrow">01 / DISCONNECTED SYSTEMS · OFFLINE SIMULATION</p><h1>Keep the message.<br><em>Wait for the link.</em></h1><p class="intro">Explore how bounded queues, delayed contacts, expiry and restarts shape reliable store-and-forward delivery.</p></div><aside class="scope"><span class="tag">RUST CORE / PYTHON VERIFIED</span><h2>Disconnected.<br>Not forgotten.</h2><p>Three invented nodes. No radios or spacecraft. Every event, queue sample and final message is checked against an independent model.</p></aside></section><section class="control-panel" aria-label="Simulation settings"><div id="controls"></div><label class="remember"><input type="checkbox" id="remember">Remember these settings on this device</label></section><p id="status" role="status" aria-live="polite">Loading simulation…</p><section id="evidence" hidden></section><section id="guide" class="guide"><p class="eyebrow">METHOD / WHAT THIS LAB DOES AND DOES NOT CLAIM</p><h2>The assumptions travel with the message.</h2><div class="guide-grid"><div><h3>01 · Hold through disruption</h3><p>Source and relay retain the original payload during flight. A full receiver refuses the transfer; the sender retries while a departure contact is open. Source admission can reject a new message rather than evict retained data.</p></div><div><h3>02 · Respect lifetime</h3><p>Expiry happens before arrivals at the same tick. Contacts are half-open departure windows, not arrival deadlines. Ticks, message sizes and topology are deliberately bounded, invented lab values.</p></div><div><h3>03 · Verify recovery</h3><p>A restart case checkpoints the complete ownership/in-flight state and resumes in a fresh worker process. CRC detects accidental corruption—not identity or malicious changes. This is not BPv7, BPSec or a distributed exactly-once protocol.</p></div></div><p><a href="https://github.com/JasonStys/delay-tolerant-mission-network-lab/blob/main/docs/USER_GUIDE.md" rel="noreferrer">User guide / model limits ↗</a> · <a href="https://github.com/JasonStys/delay-tolerant-mission-network-lab/issues" rel="noreferrer">Help / report an issue ↗</a></p></section></main><footer>Designed and engineered by <a href="https://github.com/JasonStys" rel="noreferrer">Jason Stys</a><span>SYNTHETIC · OFFLINE · NO AFFILIATION OR ENDORSEMENT</span></footer>`;

/** Construct finite selectors; no data-derived HTML can become configuration or executable code. */
function controls(): void {
  document.querySelector("#controls")!.innerHTML =
    `<label>Scenario<select id="scenario">${Object.entries(scenarios)
      .map(
        ([key, label]) =>
          `<option value="${key}" ${key === settings.scenario ? "selected" : ""}>${label}</option>`,
      )
      .join(
        "",
      )}</select></label>${(["capacity", "delay", "policy"] as const).map((key) => `<label>${{ capacity: "Retained bytes / node", delay: "One-way delay / ticks", policy: "Queue ordering" }[key]}<select id="${key}">${choices[key].map((value) => `<option value="${value}" ${settings[key] === value ? "selected" : ""}>${key === "policy" ? (value === 0 ? "Source-order FIFO" : "Earliest expiry") : value}</option>`).join("")}</select></label>`).join("")}<button id="recompute" class="primary">Run experiment ↗</button>`;
  for (const key of ["scenario", "capacity", "delay", "policy"] as const)
    document.querySelector<HTMLSelectElement>(`#${key}`)!.addEventListener("change", (event) => {
      const value = (event.target as HTMLSelectElement).value;
      settings = { ...settings, [key]: key === "scenario" ? value : Number(value) };
      void load();
    });
  document.querySelector("#recompute")!.addEventListener("click", () => void load());
}

/** Abort superseded work, hide stale outputs and render failures without trusting server error text. */
async function load(): Promise<void> {
  controller?.abort();
  const current = new AbortController();
  controller = current;
  const status = document.querySelector<HTMLElement>("#status")!,
    evidence = document.querySelector<HTMLElement>("#evidence")!;
  status.textContent = "Running Rust and independent reference…";
  evidence.hidden = true;
  try {
    if (remember)
      try {
        localStorage.setItem(storageKey, JSON.stringify(settings));
      } catch {
        /* Optional preference storage. */
      }
    const query = new URLSearchParams(
      Object.entries(settings).map(([key, value]) => [key, String(value)]),
    );
    const response = await fetch(`/api/run?${query}`, {
      signal: current.signal,
      cache: "no-store",
    });
    if (!response.ok) throw new Error("Local analysis unavailable");
    const value: unknown = await response.json();
    if (!isReport(value)) throw new Error("Invalid evidence contract");
    if (controller !== current) return;
    report = value;
    tick = 0;
    messageFilter = "all";
    render();
    evidence.hidden = false;
    status.textContent =
      "Verified: Rust and Python traces agree. Replay ticks or inspect the full ledger below.";
  } catch (error) {
    if (current.signal.aborted || controller !== current) return;
    report = null;
    status.innerHTML = `Could not verify simulation. <button id="retry">Try again</button>`;
    document.querySelector("#retry")!.addEventListener("click", () => void load());
  }
}

/** Render complete-run metrics separately from the selected post-tick state and event slice. */
function render(): void {
  if (!report) return;
  const r = report;
  const query = new URLSearchParams(
    Object.entries(settings).map(([key, value]) => [key, String(value)]),
  );
  document.querySelector("#evidence")!.innerHTML = `<div class="metrics">${[
    ["OFFERED", r.totals.offered],
    ["DELIVERED", r.totals.delivered],
    ["EXPIRED", r.totals.expired],
    ["SOURCE REJECTED", r.totals.rejected],
    ["STILL RETAINED", r.totals.retained],
  ]
    .map(([label, value]) => `<article><p>${label}</p><strong>${escape(value)}</strong></article>`)
    .join(
      "",
    )}</div><section class="panel"><div class="section-head"><div><p class="eyebrow">02 / CONTACT PLAN & REPLAY</p><h2>A link is an opportunity. Not a guarantee.</h2></div><span class="tag">SIMULATED TICKS</span></div><p>Each open hop can start one whole message per tick. Queue capacity counts retained payload bytes, including sender originals in flight. Final metrics above cover the entire experiment.</p><div class="replay-controls"><button id="previous" aria-label="Previous tick">←</button><label for="tick">Replay tick <output id="tick-label">0</output></label><input id="tick" type="range" min="0" max="${Math.max(0, bounded(r.input.horizon, 64) - 1)}" value="0" step="1"><button id="next" aria-label="Next tick">→</button><button id="last">Jump to end</button></div><div id="timeline" class="chart-region" role="region" tabindex="0" aria-label="Contact timeline; exact windows in contact table"></div><div id="network" class="network"></div><div id="tick-events" class="tick-events" aria-live="polite"></div><details><summary>Exact contact windows and phase order</summary><p>At each tick: expire retained messages → admit releases → process arrivals → start departures → record sample. A restart boundary is before that tick. Contacts are [start, end) for departures; arrivals may occur after a window closes.</p><table><thead><tr><th>Hop</th><th>Start included</th><th>End excluded</th></tr></thead><tbody>${r.input.contacts.map((c) => `<tr><td>${c.hop === 0 ? "Probe → Relay" : "Relay → Ground"}</td><td>${escape(c.start)}</td><td>${escape(c.end)}</td></tr>`).join("")}</tbody></table></details></section><section class="panel"><div class="section-head"><div><p class="eyebrow">03 / OWNERSHIP & OUTCOMES</p><h2>One logical owner. An explicit result.</h2></div></div><p>The message table reflects the selected tick. CRCs refer to the trusted original payload; this is accidental-corruption checking, not authentication. Sent messages remain retained until accepted.</p><div id="message-table"></div><div class="score-grid"><div><span>Transmission attempts</span><strong>${escape(r.totals.attempts)}</strong></div><div><span>Integrity rejections</span><strong>${escape(r.totals.integrity_rejected)}</strong></div><div><span>Receiver-full events</span><strong>${escape(r.totals.receiver_full)}</strong></div><div><span>Duplicate copies suppressed</span><strong>${escape(r.totals.duplicates)}</strong></div></div><p>Mean delivery latency / ticks: ${display(r.totals.mean_delivery_ticks, 3)}. This includes delivered messages only; it is not an overall-success statistic.</p></section><section class="panel"><div class="section-head"><div><p class="eyebrow">04 / RESTART EVIDENCE</p><h2>A fresh process. The same state.</h2></div><span class="tag">${escape(r.recovery.mode)}</span></div><p>${r.recovery.mode === "none" ? "No restart in this case. Select Restart with in-flight data to inspect a real two-worker checkpoint handoff." : `Checkpoint before tick ${escape(r.recovery.next_tick)}. The first Rust process exits; a fresh worker validates and restores the saved owner/flight state. Full results still match the independent reference.`}</p><p class="digest">CHECKPOINT SHA-256<br>${r.recovery.checkpoint_sha256 === null ? "Not applicable" : escape(r.recovery.checkpoint_sha256)}</p><p>For a committed disk handoff, use the CLI with <code>--checkpoint-store</code>. Browser runs do not write history or checkpoints to disk. This is boundary recovery, not a power-loss or distributed-transaction guarantee.</p></section><section class="panel"><div class="section-head"><div><p class="eyebrow">05 / CHRONOLOGICAL LEDGER</p><h2>No dropped context.</h2></div><label>Filter message<select id="message-filter"><option value="all">All messages</option>${r.input.messages.map((m) => `<option value="${escape(m.id)}">Message ${escape(m.id)}</option>`).join("")}</select></label></div><p>This full-run ledger is independent of replay position. Filtering changes display only, never final metrics or downloads.</p><div id="ledger"></div></section><section class="panel"><p class="eyebrow">06 / REPRODUCIBLE EVIDENCE</p><h2>Keep the assumptions with the trace.</h2><p>Source: ${escape(r.provenance.source)}. ${escape(r.provenance.reference)}.</p><div class="downloads">${["json", "csv", "html", "input"].map((format) => `<a href="/api/report?${query}&format=${format}" download>${format === "input" ? "Input JSON" : format.toUpperCase() + " report"} ↓</a>`).join("")}</div><p class="digest">REPORT SHA-256<br>${escape(r.id)}</p><details><summary>Model limits and provenance</summary><pre>${escape(JSON.stringify(r.provenance, null, 2))}</pre><ul>${r.limitations.map((text) => `<li>${escape(text)}</li>`).join("")}</ul></details></section>`;
  document.querySelector("#tick")!.addEventListener("input", (event) => {
    tick = Number((event.target as HTMLInputElement).value);
    replay();
  });
  document.querySelector("#previous")!.addEventListener("click", () => {
    tick = Math.max(0, tick - 1);
    replay();
  });
  document.querySelector("#next")!.addEventListener("click", () => {
    tick = Math.min(r.samples.length - 1, tick + 1);
    replay();
  });
  document.querySelector("#last")!.addEventListener("click", () => {
    tick = r.samples.length - 1;
    replay();
  });
  document.querySelector("#message-filter")!.addEventListener("change", (event) => {
    messageFilter = (event.target as HTMLSelectElement).value;
    ledger();
  });
  replay();
  ledger();
}

/** Draw only the inclusive post-tick state; future delivery/expiry must not appear during earlier replay. */
function replay(): void {
  if (!report) return;
  const r = report,
    sample = r.samples[tick];
  if (!sample) return;
  document.querySelector<HTMLInputElement>("#tick")!.value = String(tick);
  document.querySelector("#tick-label")!.textContent = String(tick);
  document.querySelector("#timeline")!.innerHTML = timelineSvg(
    r.input.contacts,
    r.input.horizon,
    tick,
  );
  document.querySelector("#network")!.innerHTML = [
    { name: "PROBE", value: sample.probe_bytes, node: 0 },
    { name: "RELAY", value: sample.relay_bytes, node: 1 },
    { name: "GROUND", value: sample.delivered, node: 2 },
  ]
    .map(
      (n) =>
        `<article class="node"><p class="eyebrow">${n.name}</p><strong>${escape(n.value)} <small>${n.node === 2 ? "delivered" : "/ " + settings.capacity + " bytes"}</small></strong>${n.node !== 2 ? `<svg viewBox="0 0 200 8" role="img" aria-label="Retained ${n.name.toLowerCase()} bytes"><rect class="capacity-bg" width="200" height="8"/><rect class="capacity-used" width="${(bounded(n.value, 32) / settings.capacity) * 200}" height="8"/></svg>` : "<p>Application sink · no modeled storage limit</p>"}<span>${n.node === 2 ? "Accepted after expiry and CRC checks" : r.input.contacts.some((c) => c.hop === n.node && c.start <= tick && tick < c.end) ? "Departure contact open" : "Departure contact closed"}</span></article>`,
    )
    .join("");
  const events = r.events.filter((e) => e.tick === tick);
  document.querySelector("#tick-events")!.innerHTML =
    `<b>After tick ${tick}</b> · ${escape(sample.inflight)} network copies in flight. ${events.length ? events.map((e) => `<span class="status-chip">${e.id === 0 ? "WORKER" : "M" + escape(e.id)} / ${escape(e.kind)}</span>`).join(" ") : "No transitions this tick. Retained data continues waiting."}`;
  const messages = replayMessages(r, tick);
  document.querySelector("#message-table")!.innerHTML =
    `<div class="table-scroll" tabindex="0" role="region" aria-label="Message state at selected tick"><table><thead><tr><th>Message</th><th>State now</th><th>Logical owner</th><th>Attempts so far</th><th>Delivered tick</th><th>Original CRC-32C</th></tr></thead><tbody>${messages.map((m) => `<tr><td>M${escape(m.id)}</td><td>${escape(m.status)}</td><td>${["Probe", "Relay", "Ground"][m.node] ?? "Unknown"}</td><td>${escape(m.attempts)}</td><td>${m.delivered_tick < 0 ? "Not delivered yet" : escape(m.delivered_tick)}</td><td>${escape(m.crc32c)}</td></tr>`).join("")}</tbody></table>${messages.length ? "" : "<p>No messages offered in this case.</p>"}</div>`;
}

/** Render the complete event history, optionally filtered by message but not replay time. */
function ledger(): void {
  if (!report) return;
  const events = report.events.filter(
    (e) => messageFilter === "all" || String(e.id) === messageFilter,
  );
  document.querySelector("#ledger")!.innerHTML =
    `<div class="table-scroll" tabindex="0" role="region" aria-label="Full chronological event ledger"><table><thead><tr><th>Tick</th><th>Message</th><th>Node</th><th>Transition</th></tr></thead><tbody>${events.map((e) => `<tr><td>${escape(e.tick)}</td><td>${e.id === 0 ? "WORKER" : "M" + escape(e.id)}</td><td>${["Probe", "Relay", "Ground"][e.node] ?? "Unknown"}</td><td>${escape(e.kind)}</td></tr>`).join("")}</tbody></table>${events.length ? "" : "<p>No events match this selection.</p>"}</div>`;
}

controls();
document.querySelector<HTMLInputElement>("#remember")!.checked = remember;
document.querySelector("#remember")!.addEventListener("change", (event) => {
  remember = (event.target as HTMLInputElement).checked;
  try {
    if (remember) localStorage.setItem(storageKey, JSON.stringify(settings));
    else localStorage.removeItem(storageKey);
  } catch {
    /* No remote fallback for local preference storage. */
  }
});
void load();
