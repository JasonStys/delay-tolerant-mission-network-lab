/**
 * File: native_browser.mjs
 * Purpose: Jason Stys — owned Chromium acceptance of an extracted executable's real feature.
 * Functions: runNativeJourney; variables: validated URL, output directory, version, errors.
 * Exact source locations: docs/CODE_INDEX.md. No interception replaces application responses.
 */
import assert from "node:assert/strict";
import { stat } from "node:fs/promises";
import path from "node:path";
import { chromium, expect } from "@playwright/test";

/** Invoke a repo-specific journey with owned resources; only actual loopback application requests. */
export async function runNativeJourney(journey) {
  const [raw, output, version, ...extra] = process.argv.slice(2);
  assert.equal(extra.length, 0);
  assert.match(version ?? "", /^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$/);
  const url = new URL(raw);
  assert.equal(url.protocol, "http:");
  assert.equal(url.hostname, "127.0.0.1");
  assert.ok(Number(url.port) >= 1024 && Number(url.port) <= 65535);
  assert.equal(url.pathname, "/");
  assert.equal(url.username + url.password + url.search + url.hash, "");
  const outputDirectory = path.resolve(output);
  assert.ok((await stat(outputDirectory)).isDirectory());
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ baseURL: url.href, acceptDownloads: true });
    context.setDefaultTimeout(8_000);
    context.setDefaultNavigationTimeout(10_000);
    const external = [];
    const errors = [];
    await context.route("**/*", (route) => {
      if (new URL(route.request().url()).origin !== url.origin) {
        external.push(route.request().url());
        return route.abort();
      }
      return route.continue();
    });
    const page = await context.newPage();
    page.on("pageerror", (error) => errors.push(error.message));
    assert.equal((await page.goto(url.href))?.status(), 200);
    await expect(page.locator("body")).toContainText(`v${version}`, { timeout: 8_000 });
    await journey({ page, request: context.request, baseURL: url.href, outputDirectory, version });
    assert.deepEqual(external, [], "Native UI must not make outside requests");
    assert.deepEqual(errors, [], "Native UI must not leave uncaught browser errors");
    await context.close();
    console.log("Extracted native UI feature journey passed");
  } finally {
    await browser.close();
  }
}
