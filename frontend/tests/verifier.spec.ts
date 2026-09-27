import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { EXAMPLES } from "../src/lib/verification";
import supported from "./fixtures/supported.json";
import contradicted from "./fixtures/contradicted.json";
import insufficient from "./fixtures/insufficient.json";

const cases = [
  { example: EXAMPLES[0], data: supported, label: "Supported" },
  { example: EXAMPLES[1], data: contradicted, label: "Contradicted" },
  { example: EXAMPLES[2], data: insufficient, label: "Insufficient evidence" },
];

async function chooseAndVerify(page: Page, index: number) {
  await page
    .getByRole("button", {
      name: new RegExp(EXAMPLES[index].label.replace(/[?]/g, "\\?")),
    })
    .click();
  await expect(page.getByLabel("Your legal claim")).toHaveValue(
    EXAMPLES[index].claim,
  );
  await page.getByRole("button", { name: "Verify claim", exact: true }).click();
}

for (const [index, item] of cases.entries()) {
  test(`renders ${item.label} with primary evidence and accessible controls`, async ({
    page,
  }, testInfo) => {
    await page.route("**/api/verify", async (route) => {
      expect(route.request().postDataJSON()).toEqual({
        claim: item.example.claim,
      });
      await route.fulfill({ json: item.data });
    });
    await page.goto("/");
    await chooseAndVerify(page, index);
    await expect(
      page.getByRole("heading", { name: item.label, exact: true }),
    ).toBeVisible();
    await expect(page.locator(".primary-evidence")).toContainText("Article 33");
    await expect(page.locator(".page-reference")).toContainText("52");
    await expect(
      page.getByRole("link", { name: /View official EUR-Lex source/ }),
    ).toHaveAttribute("href", "https://eur-lex.europa.eu/eli/reg/2016/679/oj");
    await expect(page.locator("body")).not.toContainText(
      /retrieval_score|entailment|MiniLM|segment_number|verification_model/,
    );
    if (index === 1) {
      await expect(
        page.getByRole("region", { name: "Claim versus primary law" }),
      ).toContainText("24 hours");
      await expect(
        page.getByRole("region", { name: "Claim versus primary law" }),
      ).toContainText("72 hours");
    } else await expect(page.locator(".claim-comparison")).toHaveCount(0);
    await page
      .getByRole("button", { name: "About verification confidence" })
      .click();
    await expect(page.getByRole("note")).toContainText(
      "not a probability of legal certainty",
    );
    await page.keyboard.press("Escape");
    await expect(page.getByRole("note")).toHaveCount(0);
    const violations = (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations;
    expect(
      violations.map(({ id, nodes }) => ({
        id,
        targets: nodes.map((node) => node.target),
      })),
    ).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath(`${item.label}.png`),
      fullPage: true,
    });
    const allEvidence = page.locator(".evidence-list > summary");
    await allEvidence.focus();
    await page.keyboard.press("Enter");
    await expect(page.locator(".additional-evidence")).toBeVisible();
    // The insufficient result's primary passage is outside the five ranked candidates.
    await expect(page.locator(".additional-evidence-card")).toHaveCount(
      index === 2 ? 5 : 4,
    );
    await expect(allEvidence).toContainText(index === 2 ? "(6)" : "(5)");
    if (index === 1) {
      expect(
        (
          await new AxeBuilder({ page })
            .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
            .analyze()
        ).violations.map(({ id, nodes }) => ({
          id,
          targets: nodes.map((node) => node.target),
        })),
      ).toEqual([]);
      await page.locator(".full-passage > summary").click();
      await expect(page.locator(".full-passage blockquote")).toContainText(
        "The processor shall notify the controller",
      );
    }
    await page.getByLabel("Your legal claim").fill("A different legal claim.");
    await expect(page.locator(".verification-report")).toHaveCount(0);
  });
}

test("staged pending state tracks the request, prevents duplicate submission, and reveals immediately", async ({
  page,
}, testInfo) => {
  let release!: () => void;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  let requests = 0;
  await page.route("**/api/verify", async (route) => {
    requests += 1;
    await pending;
    await route.fulfill({ json: supported });
  });
  await page.goto("/");
  await chooseAndVerify(page, 0);
  await expect(page.getByRole("status")).toContainText("Searching primary law");
  await expect(page.getByRole("status")).toContainText(
    "Testing claim against evidence",
  );
  await expect(
    page.getByRole("button", { name: "Verifying claim" }),
  ).toBeDisabled();
  await expect(page.getByLabel("Your legal claim")).toHaveAttribute(
    "readonly",
    "",
  );
  await expect(page.locator(".example-button").first()).toBeDisabled();
  await page.screenshot({
    path: testInfo.outputPath("loading.png"),
    fullPage: true,
  });
  release();
  await expect(
    page.getByRole("heading", { name: "Supported", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("status")).toHaveCount(0);
  expect(requests).toBe(1);
});

for (const code of [
  "SERVICE_UNAVAILABLE",
  "VERIFICATION_FAILED",
  "INVALID_RESPONSE",
  "SOURCE_UNAVAILABLE",
]) {
  test(`${code} gives a clean, retryable error`, async ({ page }) => {
    let attempts = 0;
    await page.route("**/api/verify", async (route) => {
      attempts += 1;
      await route.fulfill(
        attempts === 1 ? { status: 503, json: { code } } : { json: supported },
      );
    });
    await page.goto("/");
    await chooseAndVerify(page, 0);
    await expect(page.locator("main").getByRole("alert")).toBeVisible();
    await expect(page.getByLabel("Your legal claim")).toHaveValue(
      EXAMPLES[0].claim,
    );
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(
      page.getByRole("heading", { name: "Supported", exact: true }),
    ).toBeVisible();
    expect(attempts).toBe(2);
  });
}

test("malformed responses never produce an invented verdict", async ({
  page,
}) => {
  await page.route("**/api/verify", (route) =>
    route.fulfill({ json: { ...supported, confidence: 2 } }),
  );
  await page.goto("/");
  await chooseAndVerify(page, 0);
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "couldn’t read",
  );
  await expect(page.locator(".verification-report")).toHaveCount(0);
});

test("network failure, keyboard validation, and landing accessibility", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to verification" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByLabel("Your legal claim")).toBeFocused();
  await page.getByRole("button", { name: "Verify claim", exact: true }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "between 3 and 1,000",
  );
  await expect(page.getByLabel("Your legal claim")).toBeFocused();
  await page.getByLabel("Your legal claim").fill(EXAMPLES[0].claim);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations.map(({ id, nodes }) => ({
      id,
      targets: nodes.map((node) => node.target),
    })),
  ).toEqual([]);
  await page.getByLabel("Your legal claim").fill("");
  await page.screenshot({
    path: testInfo.outputPath("desktop.png"),
    fullPage: true,
  });
  await page.route("**/api/verify", (route) => route.abort("failed"));
  await chooseAndVerify(page, 0);
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "couldn’t reach",
  );
  await page.screenshot({
    path: testInfo.outputPath("error.png"),
    fullPage: true,
  });
});

for (const width of [320, 390, 768]) {
  test(`responsive result at ${width}px with reduced motion`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: 844 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.route("**/api/verify", (route) =>
      route.fulfill({ json: contradicted }),
    );
    await page.goto("/");
    await page.screenshot({
      path: testInfo.outputPath("mobile-landing.png"),
      fullPage: true,
    });
    await chooseAndVerify(page, 1);
    await expect(
      page.getByRole("heading", { name: "Contradicted", exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page
      .getByRole("button", { name: "About verification confidence" })
      .click();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.keyboard.press("Escape");
    if (width === 390)
      expect(
        (
          await new AxeBuilder({ page })
            .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
            .analyze()
        ).violations.map(({ id, nodes }) => ({
          id,
          targets: nodes.map((node) => node.target),
        })),
      ).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath("mobile-result.png"),
      fullPage: true,
    });
  });
}

test("short laptop viewport keeps the action and all examples visible", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Verify claim", exact: true }),
  ).toBeInViewport();
  await expect(page.locator(".example-button").last()).toBeInViewport();
  await page.screenshot({
    path: testInfo.outputPath("laptop.png"),
    fullPage: true,
  });
});

test("@live all three examples use the existing backend through the frontend proxy", async ({
  page,
}) => {
  test.setTimeout(180_000);
  test.skip(
    process.env.LEXPROOF_LIVE_TESTS !== "1",
    "Set LEXPROOF_LIVE_TESTS=1 and run the indexed backend.",
  );
  await page.goto("/");
  for (const [index, item] of cases.entries()) {
    await chooseAndVerify(page, index);
    await expect(
      page.getByRole("heading", { name: item.label, exact: true }),
    ).toBeVisible({ timeout: 125_000 });
    await expect(page.locator(".primary-evidence")).toContainText("Article 33");
  }
});
