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
  "/?vs=medicare-surcharge-2pp",
  "/explore",
  "/explore?show=reduces&sort=size",
  "/explore/tcja-full-extension",
  "/explore/corporate-28pct",
  "/explore/corporate-15pct",
  "/compare",
  "/compare?ids=corporate-28pct,corporate-15pct",
  "/compare?ids=top-rate-39-6,top-rate-45,tariff-universal-10pct",
  "/build",
  "/build?policies=corporate-28pct,estate-repeal,salt-cap-repeal",
  "/build?values=deficit-hawk",
  "/explore/top-rate-39-6?v=2020-01-01",
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
  "/changes",
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
    // A link prefetch to a server-rendered page (/compare reads its ids per request)
    // is cancelled when the check closes the page. A reader never sees it.
    if (/[?&]_rsc=/.test(req.url()) && req.failure()?.errorText === "net::ERR_ABORTED") return;
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
      untaggedStages: [...document.querySelectorAll(".headline .stage")].filter(
        (stage) => stage.querySelector(".v") && !stage.querySelector(".estimatetag"),
      ).length,
      publishedTags: [...document.querySelectorAll('.estimatetag[data-kind="published"]')].map((el) => ({
        producer: el.getAttribute("data-producer") || "",
        text: el.textContent || "",
      })),
    };
  });
  if (layout.untaggedStages) problems.push(`${layout.untaggedStages} headline figures have no estimate tag`);
  if (route === "/explore/corporate-28pct") {
    const named = layout.publishedTags.filter((tag) => tag.producer.includes("Treasury"));
    if (named.length === 0) problems.push("published tag does not name Treasury");
    if (named.some((tag) => /\bCBO\b/.test(tag.text))) problems.push("published tag names CBO");
  }
  if (route.startsWith("/compare?ids=")) {
    const cards = await page.evaluate(() =>
      [...document.querySelectorAll(".comparecard")].map((el) => Math.round(el.getBoundingClientRect().left)),
    );
    const expected = route.split("=")[1].split(",").length;
    if (cards.length !== expected) problems.push(`${cards.length} compare cards for ${expected} ids`);
    const columns = new Set(cards).size;
    if (viewport.name === "phone" && columns !== 1) problems.push("compare multiples do not stack on a phone");
    if (viewport.name === "desktop" && columns !== cards.length) problems.push("compare multiples are not side by side");
    const diff = await page.evaluate(() => document.querySelector("#difference")?.textContent ?? "");
    if (!diff) problems.push("compare page has no difference line or reason");
  }
  if (viewport.name === "desktop" && (route === "/" || route.startsWith("/?"))) {
    const fold = await page.evaluate(() => {
      const seen = (sel) => {
        const box = document.querySelector(sel)?.getBoundingClientRect();
        return !!box && box.top >= 0 && box.top < window.innerHeight;
      };
      return { chart: seen(".comparecard .smallmultiple"), figure: seen(".comparecard .v") };
    });
    if (!fold.chart) problems.push("home: no chart above the fold");
    if (!fold.figure) problems.push("home: no scored figure above the fold");
  }
  if (route.startsWith("/build?")) {
    const summary = await page.evaluate(() => {
      const block = document.querySelector(".summarytotal");
      return {
        together: !!block?.querySelector(".big") && !!block?.querySelector(".exclusion"),
        exclusion: block?.querySelector(".exclusion")?.textContent ?? "",
      };
    });
    if (!summary.together) problems.push("the exclusion sentence is not in the same block as the package total");
    if (!/Interactions between these policies are not measured/.test(summary.exclusion)) problems.push("exclusion sentence missing");
    // Scrolled halfway down the list, the total and the gap must still be on screen.
    const inView = await page.evaluate(async () => {
      window.scrollTo(0, document.documentElement.scrollHeight / 2);
      await new Promise((r) => setTimeout(r, 150));
      const box = document.querySelector(".summarytotal .big")?.getBoundingClientRect();
      return !!box && box.top >= 0 && box.bottom <= window.innerHeight;
    });
    if (!inView) problems.push("package total scrolls out of view");
    const exports = await page.evaluate(() => ({
      buttons: [...document.querySelectorAll(".packageexports button")].map((b) => b.textContent ?? ""),
      cite: document.querySelector(".packageexports .citetext")?.textContent ?? "",
    }));
    for (const label of ["Download CSV", "Download PNG", "Copy link"]) {
      if (!exports.buttons.includes(label)) problems.push(`Build exports have no ${label}`);
    }
    if (!/sum of standalone published scores/.test(exports.cite)) problems.push("Build citation does not name the package sum");
    await page.evaluate(() => window.scrollTo(0, 0));
  }
  if (route.includes("?v=2020-01-01")) {
    const notice = await page.evaluate(() => document.querySelector(".stalelink")?.textContent ?? "");
    if (!/recomputed/.test(notice)) problems.push("an old link does not say the figures were recomputed");
  }
  if (route.startsWith("/explore/") || route.startsWith("/compare?ids=")) {
    const cite = await page.evaluate(() => document.querySelector(".cite .citetext")?.textContent ?? "");
    if (!/v=\d{4}-\d{2}-\d{2}/.test(cite)) problems.push("citation has no v= link");
  }
  if (viewport.name === "desktop" && route.startsWith("/explore/")) {
    const above = await page.evaluate(() => {
      const figure = document.querySelector(".headline .v");
      if (!figure) return false;
      const box = figure.getBoundingClientRect();
      return box.top < window.innerHeight && box.bottom > 0;
    });
    if (!above) problems.push("headline figure is below the fold");
  }
  if (viewport.name === "desktop" && route === "/explore") {
    const visible = await page.evaluate(() =>
      [...document.querySelectorAll(".explorelist a")].filter((el) => {
        const box = el.getBoundingClientRect();
        return box.top < window.innerHeight && box.bottom > 80;
      }).length,
    );
    if (visible < 12) problems.push(`only ${visible} proposals visible on first load`);
  }
  const wideProse = await page.evaluate(() => {
    const nodes = [...document.querySelectorAll(".work .sentence, .work .lede, .work .note, .work header p, .work .checked p")];
    const over = [];
    for (const el of nodes) {
      const probe = document.createElement("span");
      probe.style.cssText = `position:absolute;visibility:hidden;white-space:nowrap;font:${getComputedStyle(el).font}`;
      probe.textContent = "0".repeat(75);
      document.body.appendChild(probe);
      const limit = probe.getBoundingClientRect().width;
      probe.remove();
      if (el.getBoundingClientRect().width > limit + 1) over.push(el.className || el.tagName.toLowerCase());
    }
    return over.slice(0, 4);
  });
  if (wideProse.length) problems.push(`prose wider than 75 characters (${wideProse.join(", ")})`);
  if (!layout.h1 || !layout.h1Visible) problems.push("no visible page title (h1)");
  if (layout.overflow > 1) {
    problems.push(`page is ${layout.overflow}px wider than the screen (${layout.wide.join(", ") || "element not found"})`);
  }
  problems.push(...errors);

  const file = `${route === "/" ? "home" : route.slice(1).replace(/[/?=,&]/g, "-")}-${viewport.name}.png`;
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
