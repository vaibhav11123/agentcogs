import { expect, test } from "@playwright/test";

async function tickBoxes(page: import("@playwright/test").Page, selector: string) {
  return page.locator(selector).evaluateAll((nodes) =>
    nodes
      .map((node) => {
        const box = node.getBoundingClientRect();
        return { left: box.left, right: box.right, top: box.top, bottom: box.bottom, width: box.width };
      })
      .filter((box) => box.width > 0)
  );
}

function overlaps(a: { left: number; right: number; top: number; bottom: number }, b: { left: number; right: number; top: number; bottom: number }) {
  return a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1;
}

test("date labels do not cover each other on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/demo?sample=1");
  await expect(page.getByText("Vellum Research", { exact: true })).toBeVisible();
  await page.getByText("Vellum Research", { exact: true }).click();
  await expect(page).toHaveURL(/\/customers\//);
  await expect(page.locator(".recharts-xAxis text").first()).toBeVisible();
  const boxes = await tickBoxes(page, ".recharts-xAxis text");
  expect(boxes.length).toBeGreaterThan(0);
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      expect(overlaps(boxes[i], boxes[j]), `ticks ${i} and ${j}`).toBeFalsy();
    }
  }
});

test("a narrow page does not scroll sideways and sign out is a 24px target", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await page.goto("/demo?sample=1");
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
  const box = await page.getByRole("button", { name: "Sign out" }).boundingBox();
  expect(box).not.toBeNull();
  expect(box!.width).toBeGreaterThanOrEqual(24);
  expect(box!.height).toBeGreaterThanOrEqual(24);
  const fits = await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1
  );
  expect(fits).toBeTruthy();
});

test("an alert opens the customer", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/demo?sample=1");
  await page.getByRole("link", { name: "Alerts", exact: true }).click();
  const customer = page.locator("a[href^='/customers/']").first();
  await expect(customer).toBeVisible();
  await customer.click();
  await expect(page).toHaveURL(/\/customers\//);
  await expect(page.getByRole("heading").first()).toBeVisible();
});

test("the public login does not offer an email code", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Open Patternstack" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Self-host the API" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Send code" })).toHaveCount(0);
});
