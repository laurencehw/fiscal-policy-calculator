import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { NAV_GROUPS, NAV_ITEMS } from "./nav";

test("every section in the nav has a page, and no page is listed twice", () => {
  for (const item of NAV_ITEMS) {
    const page = new URL(`../app${item.href}/page.tsx`, import.meta.url);
    assert.ok(fs.existsSync(page), `${item.href} has no page`);
    assert.ok(item.blurb.length > 0, `${item.href} has no blurb`);
  }
  assert.equal(new Set(NAV_ITEMS.map((item) => item.href)).size, NAV_ITEMS.length);
  assert.deepEqual(
    NAV_GROUPS.map((group) => group.name),
    ["Policies", "Topics", "Learn"],
  );
  const policies = NAV_GROUPS[0].items.map((item) => item.href);
  assert.deepEqual(policies, ["/explore", "/compare", "/build", "/tailor"]);
});

test("every nav page is a page the sitemap lists", () => {
  const sitemap = fs.readFileSync(new URL("../app/sitemap.ts", import.meta.url), "utf8");
  assert.match(sitemap, /NAV_ITEMS/);
  for (const item of NAV_ITEMS) {
    const page = new URL(`../app${item.href}/page.tsx`, import.meta.url);
    assert.ok(fs.existsSync(page), `${item.href} would be missing from the sitemap`);
  }
});

test("the blurbs carry no dollar figures, which would go stale between exports", () => {
  for (const item of NAV_ITEMS) assert.doesNotMatch(item.blurb, /\$[0-9]|\b\d{2,}\s+proposals/, item.href);
});
