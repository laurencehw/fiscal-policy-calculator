import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { pageMeta } from "./meta";

test("a page's share text is its own description, with the site card and a canonical", () => {
  const meta = pageMeta({ title: "Compare", description: "Side by side.", path: "/compare" });
  assert.equal(meta.description, "Side by side.");
  assert.deepEqual(meta.alternates, { canonical: "/compare" });
  const og = meta.openGraph as { description: string; title: string; images: { url: string }[] };
  assert.equal(og.description, "Side by side.");
  assert.equal(og.title, "Compare · Fiscal Policy Calculator");
  assert.equal(og.images[0].url, "/opengraph-image");
});

test("every page with a description goes through pageMeta, so none inherits the layout's share text", () => {
  const appDir = new URL("../app/", import.meta.url).pathname;
  const pages: string[] = [];
  const walk = (dir: string) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.name === "page.tsx") pages.push(full);
    }
  };
  walk(appDir);
  for (const file of pages) {
    const source = fs.readFileSync(file, "utf8");
    if (!/description:/.test(source)) continue;
    assert.match(source, /pageMeta\(/, path.relative(appDir, file));
  }
});
