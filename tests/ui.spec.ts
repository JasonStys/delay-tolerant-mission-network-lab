/** Actual three-engine native/service/UI acceptance by Jason Stys. Tests: docs/CODE_INDEX.md.
 * Normal paths use real workers and Python oracle; explicit error/security tests substitute HTTP responses only.
 */
import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("real native replay avoids future-state leakage", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#evidence")).toBeVisible();
  await expect(page.locator("#status")).toContainText("Rust and Python traces agree");
  await expect(page.locator("#message-table")).toContainText("Not delivered yet");
  await page.getByRole("button", { name: "Jump to end" }).click();
  await expect(page.locator("#message-table tbody tr").first()).toContainText("delivered");
  await expect(page.locator("#tick-label")).toHaveText("31");
  await page.getByRole("button", { name: "Previous tick", exact: true }).click();
  await expect(page.locator("#tick-label")).toHaveText("30");
});
test("fault and restart evidence are observable", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#evidence")).toBeVisible();
  await page.locator("#scenario").selectOption("restart-inflight");
  await expect(page.getByText("fresh-worker", { exact: true })).toBeVisible();
  await expect(page.locator("#ledger")).toContainText("restart");
  await page.locator("#scenario").selectOption("corrupt-first");
  await expect(page.locator("#ledger")).toContainText("integrity-rejected");
  await expect(page.locator(".score-grid")).toContainText("Integrity rejections1");
});
test("ordering and backpressure produce actual differences", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#evidence")).toBeVisible();
  await page.locator("#scenario").selectOption("priority-choice");
  await expect(page.locator("#status")).toContainText("Verified");
  await page.getByRole("button", { name: "Jump to end" }).click();
  await expect(page.locator("#message-table tbody tr").first()).toContainText("delivered");
  await page.locator("#policy").selectOption("1");
  await expect(page.locator("#status")).toContainText("Verified");
  await page.getByRole("button", { name: "Jump to end" }).click();
  await expect(page.locator("#message-table tbody tr").first()).toContainText("expired");
  await page.locator("#scenario").selectOption("queue-pressure");
  await page.locator("#capacity").selectOption("8");
  await expect(page.locator("#ledger")).toContainText("receiver-full");
});
test("downloads and filtering preserve full evidence", async ({ page, request }) => {
  await page.goto("/");
  await expect(page.locator("#evidence")).toBeVisible();
  await page.locator("#message-filter").selectOption("1");
  await expect(page.locator("#ledger tbody tr")).toHaveCount(5);
  for (const name of ["JSON report ↓", "CSV report ↓", "HTML report ↓", "Input JSON ↓"]) {
    const href = await page.getByRole("link", { name, exact: true }).getAttribute("href");
    const response = await request.get(href!);
    expect(response.status()).toBe(200);
    expect(response.headers()["content-disposition"]).toContain("attachment");
    if (name.startsWith("JSON")) expect((await response.json()).totals.delivered).toBe(3);
    if (name.startsWith("Input")) expect((await response.json()).messages).toHaveLength(3);
    if (name.startsWith("HTML")) expect(await response.text()).not.toContain("<script");
  }
});
test("preferences opt in and remove cleanly", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#evidence")).toBeVisible();
  expect(
    await page.evaluate(() => localStorage.getItem("mission-network-preferences-v1")),
  ).toBeNull();
  await page.locator("#scenario").selectOption("no-contact");
  await expect(page.locator("#status")).toContainText("Verified");
  await page.getByLabel("Remember these settings on this device").check();
  await page.reload();
  await expect(page.locator("#scenario")).toHaveValue("no-contact");
  await expect(page.locator("#evidence")).toBeVisible();
  await page.getByLabel("Remember these settings on this device").uncheck();
  expect(
    await page.evaluate(() => localStorage.getItem("mission-network-preferences-v1")),
  ).toBeNull();
});
test("worker/API failure hides stale outputs and retries", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#evidence")).toBeVisible();
  await page.route("**/api/run?**", (route) => route.fulfill({ status: 500, body: "unavailable" }));
  await page.getByRole("button", { name: "Run experiment ↗" }).click();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(page.locator("#evidence")).toBeHidden();
  await page.unroute("**/api/run?**");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.locator("#evidence")).toBeVisible();
});
test("malicious response text is inert", async ({ page }) => {
  await page.route("**/api/run?**", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.provenance.source = '<img src=x onerror="alert(1)">';
    body.events[0].kind = "<script>alert(1)</script>";
    await route.fulfill({ response, json: body });
  });
  await page.goto("/");
  await expect(page.locator("#evidence")).toBeVisible();
  await expect(page.locator("#evidence")).toContainText("<img src=x");
  await expect(page.locator("#evidence img, #evidence script")).toHaveCount(0);
});
test("mobile keyboard timeline and accessibility", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator("#evidence")).toBeVisible();
  const size = await page.evaluate(() => ({
    width: innerWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(size.scroll).toBeLessThanOrEqual(size.width + 1);
  const region = page.getByRole("region", {
    name: "Contact timeline; exact windows in contact table",
  });
  await region.focus();
  await expect(region).toBeFocused();
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze())
      .violations,
  ).toEqual([]);
});
