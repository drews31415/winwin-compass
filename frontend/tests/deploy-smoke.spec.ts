import { test, expect } from "@playwright/test";

const baseUrl = "https://golmok-compass.vercel.app";
const paths = ["/", "/chat", "/map", "/report", "/policy"];

for (const path of paths) {
  test(`smoke ${path}`, async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (message) => {
      if (message.type() === "error") {
        errors.push(message.text());
      }
    });
    page.on("pageerror", (error) => {
      errors.push(error.message);
    });

    const response = await page.goto(`${baseUrl}${path}`, {
      waitUntil: "networkidle",
      timeout: 60000,
    });

    expect(response?.ok()).toBeTruthy();
    expect(errors).toEqual([]);
  });
}
