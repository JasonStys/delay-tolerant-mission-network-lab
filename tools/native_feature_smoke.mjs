/**
 * Frozen-app message-waterfall acceptance by Jason Stys.
 * Function: runNativeJourney callback; variables: actual traces, downloads and elapsed ticks.
 * Only the owned compiled service is used; no HTTP mocks or external traffic.
 * Symbol locations: docs/CODE_INDEX.md.
 */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { expect } from "@playwright/test";
import { runNativeJourney } from "./native_browser.mjs";

await runNativeJourney(async ({ page, request }) => {
  await page.goto("/");
  await expect(page.locator("#evidence")).toBeVisible();
  await expect(page.locator("#waterfalls details")).toHaveCount(3);
  await expect(page.locator("#message-table")).toContainText("Not delivered yet");
  await page.locator("#waterfalls summary").first().click();
  await expect(page.locator("#waterfalls")).toContainText("in-flight-hop-0");
  const response = await request.get("/api/run");
  assert.equal(response.status(), 200);
  const report = await response.json();
  assert.equal(report.totals.delivered, 3);
  for (const row of report.waterfalls) {
    assert.equal(row.queue_ticks + row.in_flight_ticks, row.observed_elapsed_ticks);
    assert.equal(
      row.spans.reduce((total, span) => total + span.end - span.start, 0),
      report.input.horizon,
    );
  }
  const pending = page.waitForEvent("download");
  await page.getByRole("link", { name: "JSON report ↓", exact: true }).click();
  const downloaded = await pending;
  const exported = JSON.parse(await readFile(await downloaded.path(), "utf8"));
  assert.deepEqual(exported.waterfalls, report.waterfalls);
  await page.locator("#scenario").selectOption("corrupt-first");
  await expect(page.locator("#status")).toContainText("Verified");
  await page.locator("#waterfalls summary").first().click();
  await expect(page.locator("#waterfalls details").first()).toContainText(
    "integrity rejected events: 1",
  );
  await page.locator("#scenario").selectOption("empty-network");
  await expect(page.locator("#waterfalls")).toContainText("No messages supplied.");
});
