import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const paths = ["/", "/demo?sample=1"];

for (const path of paths) {
  test(`axe finds no WCAG A or AA violation on ${path}`, async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(path);
    if (path.startsWith("/demo")) {
      await expect(page.getByText("Vellum Research", { exact: true })).toBeVisible();
    } else {
      await expect(page.getByRole("button", { name: "Open Patternstack" })).toBeVisible();
    }
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });
}
