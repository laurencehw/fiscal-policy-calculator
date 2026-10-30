// Renders each page of the built site at a desktop and a phone width and fails
// on what a reader would see as broken: a page that does not load, a missing
// title, a page wider than the screen, or a script error. Screenshots are
// written to the output directory so CI can upload them for a look.
//
//   node scripts/layout-check.mjs [baseUrl] [outDir]
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const BASE = (process.argv[2] ?? "http://localhost:3000").replace(/\/$/, "");
const OUT = process.argv[3] ?? "layout-shots";

export const PAGES = [
  "/",
  "/explore",
  "/explore/tcja-full-extension",
  "/build",
  "/tailor",
  "/social-security",
  "/states",
  "/generations",
  "/tracker",
  "/ask",
  "/classroom",
  "/methods",
  "/about",
  "/contact",
  "/privacy",
];

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "phone", width: 390, height: 844 },
];

// The scoring engine is a separate service. Without it, client calls to /api/*
// fail; that is the engine's health, which public-app-health.yml watches.
const ENGINE_PATH = /\/api\//;

async function checkPage(browser, route, viewport) {
  const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height } });
  const errors = [];
  page.on("pageerror", (err) => errors.push(`script error: ${err.message}`));
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const where = msg.location()?.url ?? "";
    if (ENGINE_PATH.test(where) || ENGINE_PATH.test(msg.text())) return;
    errors.push(`console error: ${msg.text()}`);
  });
  page.on("requestfailed", (req) => {
    if (ENGINE_PATH.test(req.url())) return;
    errors.push(`request failed: ${req.url()} (${req.failure()?.errorText})`);
  });

  const problems = [];
  const response = await page.goto(BASE + route, { waitUntil: "networkidle", timeout: 60_000 });
  if (!response || response.status() !== 200) problems.push(`status ${response?.status() ?? "none"}`);
  await page.waitForTimeout(500);

  const layout = await page.evaluate(() => {
    const h1 = document.querySelector("h1");
    const rect = h1?.getBoundingClientRect();
    const wide = [];
    for (const el of document.body.querySelectorAll("*")) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.right <= window.innerWidth + 1) continue;
      // Content inside a scroll container is meant to be wider than the screen.
      let scrolls = false;
      for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
        const ox = getComputedStyle(p).overflowX;
        if (ox === "auto" || ox === "scroll" || ox === "hidden" || ox === "clip") { scrolls = true; break; }
      }
      if (!scrolls) wide.push(`${el.tagName.toLowerCase()}${el.className ? "." + String(el.className).split(" ")[0] : ""}`);
    }
    return {
      overflow: document.documentElement.scrollWidth - window.innerWidth,
      h1: h1 ? h1.textContent.trim() : null,
      h1Visible: !!rect && rect.width > 0 && rect.height > 0,
      wide: wide.slice(0, 5),
    };
  });
  if (!layout.h1 || !layout.h1Visible) problems.push("no visible page title (h1)");
  if (layout.overflow > 1) {
    problems.push(`page is ${layout.overflow}px wider than the screen (${layout.wide.join(", ") || "element not found"})`);
  }
  problems.push(...errors);

  const file = `${route === "/" ? "home" : route.slice(1).replaceAll("/", "-")}-${viewport.name}.png`;
  await page.screenshot({ path: path.join(OUT, file), fullPage: true });
  await page.close();
  return problems;
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch(
    process.env.PLAYWRIGHT_CHROMIUM_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH } : {},
  );
  let failed = 0;
  for (const route of PAGES) {
    for (const viewport of VIEWPORTS) {
      const problems = await checkPage(browser, route, viewport);
      const label = `${route} @ ${viewport.name}`;
      if (problems.length) {
        failed += 1;
        console.log(`FAIL ${label}`);
        for (const p of problems) console.log(`     ${p}`);
      } else {
        console.log(`ok   ${label}`);
      }
    }
  }
  await browser.close();
  console.log(`\n${PAGES.length * VIEWPORTS.length - failed} of ${PAGES.length * VIEWPORTS.length} page views clean; screenshots in ${OUT}/`);
  if (failed) process.exit(1);
}

await main();
