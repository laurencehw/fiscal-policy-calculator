import { test } from "node:test";
import assert from "node:assert/strict";
import { lawCatalog } from "./data";
import {
  DEFAULT_LAW,
  displayedPublished,
  displayedScore,
  lawFromQuery,
  lawInfo,
  parseLaw,
  presentPreset,
  withLaw,
} from "./lawBaseline";

const catalog = lawCatalog();

test("unknown law values fall back to current, and the default is omitted from the URL", () => {
  assert.equal(parseLaw(null), "current");
  assert.equal(parseLaw("PRE2025"), "pre2025");
  assert.equal(parseLaw("nope"), "current");
  assert.equal(lawFromQuery("?sort=size&law=extended"), "extended");
  assert.equal(lawFromQuery("?law=bogus"), "current");
  assert.equal(withLaw("/explore/tcja-full-extension", "current"), "/explore/tcja-full-extension");
  assert.equal(withLaw("/explore/tcja-full-extension", "pre2025"), "/explore/tcja-full-extension?law=pre2025");
  assert.equal(withLaw("/explore?sort=size", "extended"), "/explore?sort=size&law=extended");
  assert.equal(withLaw("/explore?law=pre2025&sort=size", "current"), "/explore?sort=size");
  assert.equal(withLaw("/explore/a?v=2026-11-05#exports", "pre2025"), "/explore/a?v=2026-11-05&law=pre2025#exports");
});

test("TCJA extension is $0 on current law and the stored reconstruction on pre-2025 law", () => {
  const current = presentPreset(catalog, "tcja-full-extension", "current");
  assert.equal(current.kind, "already_law");
  assert.equal(displayedScore(4581.9, current), 0);
  assert.equal(displayedPublished(4600, current), null);
  assert.match(current.explanation ?? "", /double-count/);
  assert.match(current.identity_baseline, /CBO Feb 2026/);

  const pre = presentPreset(catalog, "tcja-full-extension", "pre2025");
  assert.equal(pre.kind, "reconstruction");
  assert.equal(displayedScore(4581.9, pre), 4581.9);
  assert.equal(pre.score_is_on_this_law, true);
  assert.equal(pre.identity_baseline, "pre-2025 law");

  const extended = presentPreset(catalog, "tcja-full-extension", "extended");
  assert.equal(displayedScore(4581.9, extended), 0);
});

test("a live proposal keeps its stored score and says when it is not on the yardstick", () => {
  const current = presentPreset(catalog, "corporate-28pct", "current");
  assert.equal(current.kind, "live");
  assert.equal(displayedScore(-1347, current), -1347);
  assert.equal(current.explanation, null);

  const pre = presentPreset(catalog, "corporate-28pct", "pre2025");
  assert.equal(pre.score_is_on_this_law, false);
  assert.equal(displayedScore(-1347, pre), -1347);
  assert.match(pre.explanation ?? "", /not yet computed/);
});

test("a partial IRA repeal is not printed as a current-law score", () => {
  const current = presentPreset(catalog, "ira-clean-energy-repeal", "current");
  assert.equal(current.kind, "remainder_unscored");
  assert.equal(displayedScore(-800, current), null);
  assert.equal(displayedPublished(-851, current), null);
  const pre = presentPreset(catalog, "ira-clean-energy-repeal", "pre2025");
  assert.equal(displayedScore(-800, pre), -800);
});

test("the catalog sources the baseline differences and marks the extension figure approximated", () => {
  assert.equal(catalog.default, DEFAULT_LAW);
  assert.deepEqual(catalog.laws.map((row) => row.id), ["current", "pre2025", "extended"]);
  assert.equal(catalog.figures.pl119_21_conventional.billions, 3400);
  assert.equal(catalog.figures.pl119_21_outlook.billions, 4700);
  assert.equal(catalog.figures.pl119_21_outlook.approximated, false);
  assert.match(catalog.figures.pl119_21_outlook.url, /62105/);
  assert.equal(catalog.figures.temps_extended_primary.billions, 1900);
  assert.equal(catalog.figures.temps_extended_primary.approximated, true);
  assert.match(catalog.figures.temps_extended_primary.url, /crfb.org/);
  assert.equal(catalog.figures.house_passed_temps.approximated, true);
  assert.match(lawInfo(catalog, "current").lesson, /P\.L\. 119-21/);
  assert.match(catalog.worked_example, /\$0/);
  assert.match(catalog.worked_example, /temporary/i);
});
