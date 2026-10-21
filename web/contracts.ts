/** Typed replay, finite controls and safe SVG geometry by Jason Stys.
 * Types/functions/variables and exact lines: docs/CODE_INDEX.md. No HTML from source messages is trusted.
 */
export interface Settings {
  scenario: string;
  capacity: number;
  delay: number;
  policy: number;
}
export interface Event {
  tick: number;
  id: number;
  node: number;
  kind: string;
}
export interface Sample {
  tick: number;
  probe_bytes: number;
  relay_bytes: number;
  inflight: number;
  delivered: number;
  expired: number;
  rejected: number;
}
export interface Message {
  id: number;
  status: string;
  node: number;
  attempts: number;
  delivered_tick: number;
  crc32c: string;
}
export interface InputMessage {
  id: number;
  release: number;
  ttl: number;
  payload_hex: string;
}
export interface Contact {
  hop: number;
  start: number;
  end: number;
}
export interface Report {
  schema: number;
  name: string;
  id: string;
  settings: Settings;
  input: {
    name: string;
    horizon: number;
    restart_tick: number;
    fault: number;
    messages: InputMessage[];
    contacts: Contact[];
  };
  totals: {
    offered: number;
    delivered: number;
    expired: number;
    rejected: number;
    retained: number;
    unreleased: number;
    attempts: number;
    integrity_rejected: number;
    receiver_full: number;
    duplicates: number;
    mean_delivery_ticks: number | null;
  };
  provenance: Record<string, string>;
  limitations: string[];
  events: Event[];
  samples: Sample[];
  messages: Message[];
  recovery: {
    mode: string;
    next_tick: number | null;
    checkpoint_hex: string | null;
    checkpoint_sha256: string | null;
  };
}
export const scenarios: Record<string, string> = {
  "intermittent-relay": "Intermittent relay",
  "queue-pressure": "Queue and backpressure",
  "expiry-boundary": "Expiry before arrival",
  "corrupt-first": "Corruption and retry",
  "duplicate-copy": "Duplicate copy suppression",
  "restart-inflight": "Restart with in-flight data",
  "priority-choice": "FIFO versus earliest deadline",
  "no-contact": "No contact / retained data",
  "empty-network": "Empty network",
};
export const choices = { capacity: [8, 16, 32], delay: [1, 3, 5], policy: [0, 1] };
export const defaults: Settings = {
  scenario: "intermittent-relay",
  capacity: 16,
  delay: 3,
  policy: 0,
};

/** Escape dynamic text and attributes, including unexpected primitive response values. */
export function escape(value: unknown): string {
  return String(value).replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!,
  );
}
/** Null/malformed metrics remain unavailable instead of becoming misleading numeric zero. */
export function display(value: unknown, digits = 0): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toFixed(digits)
    : "Not available";
}
/** Validate numeric geometry before using a response value in SVG markup. */
export function bounded(value: unknown, maximum: number): number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= maximum
    ? value
    : 0;
}
/** Reject unsupported top-level responses; every dynamic field is still escaped during rendering. */
export function isReport(value: unknown): value is Report {
  if (!value || typeof value !== "object") return false;
  const row = value as Record<string, unknown>;
  return (
    row.schema === 1 &&
    typeof row.id === "string" &&
    /^[a-f0-9]{64}$/.test(row.id) &&
    ["events", "samples", "messages"].every(
      (key) =>
        Array.isArray(row[key]) &&
        (row[key] as unknown[]).length <= 20000 &&
        (row[key] as unknown[]).every((v) => !!v && typeof v === "object"),
    ) &&
    ["input", "settings", "totals", "recovery", "provenance"].every(
      (key) => !!row[key] && typeof row[key] === "object",
    ) &&
    Array.isArray(row.limitations) &&
    row.limitations.every((v) => typeof v === "string")
  );
}
/** Opt-in preference parsing rejects inherited scenarios, booleans/coercions and extra keys. */
export function parsePreferences(raw: string | null): Settings | null {
  try {
    const value: unknown = JSON.parse(raw ?? "null");
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    const row = value as Record<string, unknown>;
    if (
      Object.keys(row).sort().join(",") !== Object.keys(defaults).sort().join(",") ||
      typeof row.scenario !== "string" ||
      !Object.hasOwn(scenarios, row.scenario)
    )
      return null;
    for (const key of ["capacity", "delay", "policy"] as const)
      if (typeof row[key] !== "number" || !choices[key].includes(row[key])) return null;
    return row as unknown as Settings;
  } catch {
    return null;
  }
}
/** Reconstruct message state through an inclusive tick without applying future final outcomes early. */
export function replayMessages(report: Report, tick: number): Message[] {
  const messages = report.input.messages.map((m) => ({
    id: m.id,
    status: "unreleased",
    node: 0,
    attempts: 0,
    delivered_tick: -1,
    crc32c: report.messages.find((f) => f.id === m.id)?.crc32c ?? "",
  }));
  for (const event of report.events) {
    if (event.tick > tick) continue;
    const message = messages.find((m) => m.id === event.id);
    if (!message) continue;
    if (event.kind === "queued") message.status = "retained";
    if (event.kind === "source-rejected") message.status = "rejected";
    if (event.kind === "sent") message.attempts++;
    if (event.kind === "relayed") message.node = 1;
    if (event.kind === "expired") message.status = "expired";
    if (event.kind === "delivered") {
      message.status = "delivered";
      message.node = 2;
      message.delivered_tick = event.tick;
    }
  }
  return messages;
}
/** Two directed half-open departure lanes with an explicit selected-tick cursor and no physical units. */
export function timelineSvg(contacts: Contact[], horizon: number, tick: number): string {
  const span = Math.max(1, bounded(horizon, 64));
  const x = (value: unknown) => 100 + (bounded(value, 64) / span) * 600;
  const windows = contacts
    .map(
      (c) =>
        `<rect class="contact-window" x="${x(c.start)}" y="${c.hop === 0 ? 27 : 75}" width="${Math.max(0, x(c.end) - x(c.start))}" height="24"/>`,
    )
    .join("");
  const marks = Array.from({ length: 9 }, (_, i) => {
    const value = Math.round((i * span) / 8);
    return `<path class="grid-line" d="M ${x(value)} 15 V 112"/><text x="${x(value)}" y="132">${value}</text>`;
  }).join("");
  return `<svg viewBox="0 0 750 145" role="img" aria-label="Synthetic departure contact windows. Probe to relay and relay to ground. Cursor at tick ${bounded(tick, 63)}. Exact intervals in contact table.">${marks}<text x="0" y="43">PROBE → RELAY</text><text x="0" y="91">RELAY → GROUND</text>${windows}<path class="cursor" d="M ${x(tick)} 12 V 112"/></svg>`;
}
