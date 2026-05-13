const path = require("path");

function loadPlaywright() {
  try {
    return require("playwright");
  } catch (error) {
    const frontendPlaywright = path.resolve(__dirname, "../../frontend/node_modules/playwright");
    return require(frontendPlaywright);
  }
}

const { chromium } = loadPlaywright();

const BASE_URL = process.env.DEMO_URL || "https://winwin-compass.vercel.app";
const SCREENSHOT_DIR = path.resolve(__dirname, "../../screenshots");

async function waitForReady(page) {
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(2500);
}

async function safeClick(page, selector) {
  const target = page.locator(selector).first();
  if (await target.count()) {
    await target.click().catch(() => undefined);
  }
}

async function capture(page, route, filename, prepare) {
  const url = `${BASE_URL}${route}`;
  console.log(`[capture] ${url}`);
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await waitForReady(page);
  if (prepare) {
    await prepare(page);
    await page.waitForTimeout(2000);
  }
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, filename),
    fullPage: true,
  });
}

async function main() {
  const fs = require("fs");
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();

  await capture(page, "/", "01_home.png");

  await capture(page, "/chat", "02_chat.png", async (chatPage) => {
    const input = chatPage.locator("textarea").first();
    if (await input.count()) {
      await input.fill("강북구 저자본 카페 추천해줘");
      await chatPage.keyboard.press("Enter");
      await chatPage.waitForTimeout(9000);
    }
  });

  await capture(page, "/map", "03_map.png");
  await capture(page, "/report/3110016", "04_report.png");
  await capture(page, "/report/3110016", "05_forecast.png", async (reportPage) => {
    await reportPage.evaluate(() => {
      const headings = Array.from(document.querySelectorAll("h2, h3, section"));
      const target = headings.find((el) => /예측|전망|Forecast/i.test(el.textContent || ""));
      target?.scrollIntoView({ block: "center" });
    });
  });
  await capture(page, "/policy", "06_policy.png", async (policyPage) => {
    await safeClick(policyPage, "button:has-text('맞춤 정책 찾기')");
  });
  await capture(page, "/ux-test", "07_ux_test.png");

  await browser.close();
  console.log(`Screenshots saved to ${SCREENSHOT_DIR}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
