import { expect, test } from "@playwright/test";

test("sample leaderboard shows the cap and keeps dollar ticks inside the chart", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/demo?sample=1");
  await expect(page.getByText("Vellum Research", { exact: true })).toBeVisible();
  await expect(page.getByText("cap $5,822")).toBeVisible();
  await expect(page.getByText("Ashworth Counsel")).toBeVisible();

  const chart = page.locator(".recharts-wrapper").first();
  await expect(chart).toBeVisible();
  const chartBox = await chart.boundingBox();
  expect(chartBox).not.toBeNull();

  const ticks = page.locator(".recharts-yAxis text");
  const count = await ticks.count();
  expect(count).toBeGreaterThan(0);
  for (let i = 0; i < count; i++) {
    const text = ((await ticks.nth(i).textContent()) ?? "").trim();
    expect(text.startsWith("$"), `tick ${i} was ${JSON.stringify(text)}`).toBeTruthy();
    const box = await ticks.nth(i).boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(chartBox!.x - 1);
    expect(box!.x + box!.width).toBeLessThanOrEqual(chartBox!.x + chartBox!.width + 1);
  }

  const plan = page.locator("aside").getByText(/^sample$/i);
  await expect(plan).toBeVisible();
  const planBox = await plan.boundingBox();
  expect(planBox).not.toBeNull();
  expect(planBox!.y + planBox!.height).toBeLessThanOrEqual(800);
});

test("a phone can sign out and the page does not scroll sideways", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 });
  await page.goto("/demo?sample=1");
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
  const fits = await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1
  );
  expect(fits).toBeTruthy();
});
