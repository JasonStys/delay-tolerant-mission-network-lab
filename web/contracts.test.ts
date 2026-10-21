/** Replay, geometry and finite preference tests by Jason Stys. Definitions: docs/CODE_INDEX.md. */
import { expect, test } from "vitest";
import {
  bounded,
  defaults,
  display,
  escape,
  isReport,
  parsePreferences,
  replayMessages,
  timelineSvg,
  type Report,
} from "./contracts";
test("escapes text and attribute delimiters", () =>
  expect(escape('<img x="a">&\'')).toBe("&lt;img x=&quot;a&quot;&gt;&amp;&#39;"));
test("unavailable values remain explicit", () => {
  expect(display(null)).toBe("Not available");
  expect(display("4")).toBe("Not available");
  expect(display(1, 2)).toBe("1.00");
});
test("geometry rejects nonfinite negative or string values", () => {
  for (const value of [null, "8", -1, 33, Infinity, NaN]) expect(bounded(value, 32)).toBe(0);
  expect(bounded(16, 32)).toBe(16);
});
test("timeline remains finite when empty", () =>
  expect(timelineSvg([], 32, 0)).not.toMatch(/NaN|Infinity/));
test("timeline shows two directed half-open lanes", () => {
  const svg = timelineSvg([{ hop: 0, start: 1, end: 4 }], 32, 3);
  expect(svg).toContain("PROBE → RELAY");
  expect(svg).toContain("Cursor at tick 3");
  expect(svg).toContain('width="56.25"');
});
test("valid preferences survive round trip", () =>
  expect(parsePreferences(JSON.stringify(defaults))).toEqual(defaults));
test("inherited scenario names are rejected", () => {
  for (const scenario of ["constructor", "__proto__", "unknown"])
    expect(parsePreferences(JSON.stringify({ ...defaults, scenario }))).toBeNull();
});
test("extra coercion and invalid options are rejected", () => {
  for (const raw of [
    null,
    "[]",
    "{",
    JSON.stringify({ ...defaults, delay: "3" }),
    JSON.stringify({ ...defaults, policy: true }),
    JSON.stringify({ ...defaults, extra: 1 }),
    JSON.stringify({ ...defaults, capacity: 100 }),
  ])
    expect(parsePreferences(raw)).toBeNull();
});
test("invalid response envelopes fail", () => {
  for (const value of [null, {}, [], { schema: 1, id: "bad" }]) expect(isReport(value)).toBe(false);
});
const sample = {
  input: { messages: [{ id: 1, release: 0, ttl: 10, payload_hex: "aa" }] },
  messages: [
    { id: 1, status: "delivered", node: 2, attempts: 2, delivered_tick: 5, crc32c: "known" },
  ],
  events: [
    { tick: 0, id: 1, node: 0, kind: "queued" },
    { tick: 0, id: 1, node: 0, kind: "sent" },
    { tick: 2, id: 1, node: 1, kind: "relayed" },
    { tick: 3, id: 1, node: 1, kind: "sent" },
    { tick: 5, id: 1, node: 2, kind: "delivered" },
  ],
} as Report;
test("replay does not reveal future delivery", () => {
  const state = replayMessages(sample, 0)[0];
  expect(state?.status).toBe("retained");
  expect(state?.node).toBe(0);
  expect(state?.attempts).toBe(1);
  expect(state?.delivered_tick).toBe(-1);
});
test("replay advances logical owner before final delivery", () => {
  expect(replayMessages(sample, 2)[0]?.node).toBe(1);
  expect(replayMessages(sample, 5)[0]?.delivered_tick).toBe(5);
});
test("restart and duplicate events do not create extra messages", () => {
  const run = {
    ...sample,
    events: [
      ...sample.events,
      { tick: 6, id: 0, node: 0, kind: "restart" },
      { tick: 6, id: 1, node: 1, kind: "duplicate-suppressed" },
    ],
  };
  expect(replayMessages(run, 6)).toHaveLength(1);
  expect(replayMessages(run, 6)[0]?.status).toBe("delivered");
});
