const path = require("path");

function loadPlaywright() {
  try {
    return require("playwright");
  } catch {
    return require(path.join(__dirname, "..", "frontend", "node_modules", "playwright"));
  }
}

const { chromium } = loadPlaywright();

function getArgValue(name) {
  const prefix = `--${name}=`;
  const arg = process.argv.find((item) => item.startsWith(prefix));
  return arg ? arg.slice(prefix.length) : null;
}

const BASE_URL =
  getArgValue("url") ||
  process.env.DEMO_URL ||
  (process.argv.includes("--prod")
    ? "https://winwin-compass.vercel.app"
    : "http://localhost:3000");

const API_URL = process.env.API_URL || "http://localhost:8000";

async function firstVisible(page, selectors) {
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    if ((await locator.count()) > 0 && (await locator.isVisible().catch(() => false))) {
      return locator;
    }
  }
  return null;
}

async function typeSlowly(locator, text, delay = 55) {
  await locator.click();
  for (const char of text) {
    await locator.type(char, { delay });
  }
}

async function recordDemo() {
  console.log(`DEMO_URL=${BASE_URL}`);
  console.log(`API_URL=${API_URL}`);

  const browser = await chromium.launch({
    headless: false,
    slowMo: 800,
    args: ["--window-size=1440,900"],
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: {
      dir: "demo_videos/",
      size: { width: 1440, height: 900 },
    },
  });

  const page = await context.newPage();
  const query = "5천만으로 마포구 30대 여성 타겟 카페 창업 분석해줘";

  console.log("[1/6] 홈 화면 접속...");
  await page.goto(BASE_URL, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  console.log("[2/6] 검색창 입력...");
  const searchInput = await firstVisible(page, [
    'input[placeholder*="상권"]',
    'input[name="q"]',
    "main input",
    "input",
    'textarea[placeholder*="상권"]',
  ]);
  if (searchInput) {
    await typeSlowly(searchInput, query, 60);
    await page.waitForTimeout(1000);
  } else {
    console.warn("홈 검색창을 찾지 못해 다음 단계로 이동합니다.");
  }

  console.log("[3/6] 채팅 페이지 이동 및 질문 전송...");
  await page.goto(`${BASE_URL}/chat?q=${encodeURIComponent(query)}`, {
    waitUntil: "networkidle",
  });
  await page.waitForTimeout(1500);

  const chatInput = await firstVisible(page, [
    "textarea",
    'input[placeholder*="질문"]',
    'input[placeholder*="메시지"]',
  ]);
  if (chatInput) {
    const current = await chatInput.inputValue().catch(() => "");
    if (!current) {
      await typeSlowly(chatInput, query, 50);
    }
    await page.waitForTimeout(500);
    await page.keyboard.press("Enter");
    await page.waitForTimeout(8000);
  } else {
    console.warn("채팅 입력창을 찾지 못해 대기 화면만 촬영합니다.");
    await page.waitForTimeout(5000);
  }

  console.log("[4/6] 지도 페이지...");
  await page.goto(`${BASE_URL}/map`, { waitUntil: "networkidle" });
  await page.waitForTimeout(3000);

  const reportButton = page
    .locator('a:has-text("상세"), button:has-text("상세"), a:has-text("리포트")')
    .first();
  if ((await reportButton.count()) > 0 && (await reportButton.isVisible().catch(() => false))) {
    await reportButton.click();
    await page.waitForTimeout(2500);
  }

  console.log("[5/6] 리포트 페이지 (종로3가)...");
  await page.goto(`${BASE_URL}/report/3110016`, { waitUntil: "networkidle" });
  await page.waitForTimeout(5000);

  console.log("[6/6] 정책 매칭...");
  await page.goto(`${BASE_URL}/policy`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  const businessSelect = page.locator("select").first();
  if ((await businessSelect.count()) > 0 && (await businessSelect.isVisible().catch(() => false))) {
    await businessSelect.selectOption({ label: "카페" }).catch(async () => {
      await businessSelect.selectOption({ index: 0 }).catch(() => undefined);
    });
  }

  const budgetInput = await firstVisible(page, [
    'input[name*="capital"]',
    'input[placeholder*="예산"]',
    'input[type="number"]',
  ]);
  if (budgetInput) {
    await budgetInput.fill("5000").catch(() => undefined);
  }

  const submitBtn = page
    .locator('button:has-text("찾기"), button:has-text("매칭"), button:has-text("정책")')
    .first();
  if ((await submitBtn.count()) > 0 && (await submitBtn.isVisible().catch(() => false))) {
    await submitBtn.click();
    await page.waitForTimeout(4000);
  }

  await context.close();
  await browser.close();
  console.log("✅ 시연 영상 저장 완료: demo_videos/");
}

recordDemo().catch(async (error) => {
  console.error(error);
  process.exitCode = 1;
});
