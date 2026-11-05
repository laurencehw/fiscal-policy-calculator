import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { homeCandidates, homePair, homeRowLine, homeSectionText, STARTING_POINTS, tierPhrase, trustStrip, WORKED_POLICY_IDS, workedRows } from "./home";
import { DEFAULT_PAIR } from "./compare";
import { money } from "./format";
import { evidence, preset, presets, scorecardEntries, tierOf } from "./data";
import { contactText, privacyText } from "./legal";

test("the homepage section names both figures and reads them from the export", () => {
  const text = homeSectionText();
  assert.ok(text.length >= 500, `section is ${text.length} characters`);
  assert.match(text, /conventional ten-year estimate/);
  assert.match(text, /published list price/);
  const rows = workedRows();
  assert.deepEqual(rows.map((row) => row.id), [...WORKED_POLICY_IDS]);
  for (const row of rows) {
    const entry = scorecardEntries().find((item) => item.policy_id === row.id);
    assert.ok(entry, row.id);
    assert.equal(tierOf(entry), "out_of_sample", row.id);
    assert.equal(row.tier, "out_of_sample", row.id);
    const line = homeRowLine(row);
    assert.ok(text.includes(line), row.id);
    assert.ok(line.includes(money(entry.model_10yr_billions)), row.id);
    assert.ok(line.includes(money(entry.official_10yr_billions)), row.id);
    assert.match(line, /Out-of-sample prediction/);
    assert.doesNotMatch(line, /Fitted/);
  }
});

test("a fitted row is never presented without the word fitted", () => {
  assert.match(tierPhrase("fitted", 0.4), /Fitted/);
  assert.doesNotMatch(tierPhrase("out_of_sample", 1.3), /Fitted/);
  const ordinary = evidence().out_of_sample_classes.ordinary_rate_change;
  const rows = workedRows();
  assert.ok(rows[0].gapPct < 5, `close example is ${rows[0].gapPct}`);
  assert.ok(Math.abs(rows[1].gapPct - ordinary.mean_abs_error) < 2, `class-mean example is ${rows[1].gapPct}`);
  assert.ok(rows[2].gapPct > 40, `miss example is ${rows[2].gapPct}`);
  assert.equal(rows[2].id, "cbo_opt64_corporate_rate_1pp");
});

test("the homepage does not hardcode a dollar figure", () => {
  for (const file of ["home.ts", "../app/page.tsx"]) {
    const source = fs.readFileSync(new URL(file, import.meta.url), "utf8");
    assert.doesNotMatch(source, /\$[0-9]/, file);
    assert.doesNotMatch(source, /\b2700\b/, file);
    assert.doesNotMatch(source, /\b1426\.8\b/, file);
  }
});

test("contact and privacy are real pages, with no street address", () => {
  assert.ok(contactText().length >= 500, `contact is ${contactText().length}`);
  assert.ok(privacyText().length >= 500, `privacy is ${privacyText().length}`);
  assert.match(contactText(), /lw3387@nyu\.edu/);
  assert.match(privacyText(), /Anthropic/);
  assert.match(privacyText(), /not stored/);
  assert.doesNotMatch(`${contactText()} ${privacyText()}`, /streetAddress|PostalAddress|\d{5}(?:-\d{4})?/);
});

test("Explore labels a figure published only when the export says it is", () => {
  const unpublished = presets()
    .filter((row) => row.cbo_score !== null && !row.cbo_published)
    .map((row) => row.id)
    .sort();
  assert.deepEqual(unpublished, [
    "carbon-tax-50",
    "drug-negotiation-expand",
    "drug-reference-pricing",
    "tcja-extension-no-salt-cap",
  ]);
  const source = fs.readFileSync(new URL("../app/explore/page.tsx", import.meta.url), "utf8");
  assert.match(source, /cbo_published/);
});

test("the home compare never shows a fitted row or an unfitted reconstruction", () => {
  const candidates = homeCandidates();
  assert.ok(candidates.length >= 2);
  for (const c of candidates) {
    const cred = preset(c.id)!.conventional.credibility!;
    assert.notEqual(cred.own_row_tier, "fitted", c.id);
    assert.notEqual(cred.own_row_tier, "reconstruction", c.id);
    assert.ok(cred.own_row_tier === "out_of_sample" || cred.n_tier1_rows > 0, c.id);
    assert.match(c.basis, /^out-of-sample/);
  }
  assert.ok(!candidates.some((c) => c.id.startsWith("corporate-")));
  const ids = candidates.map((c) => c.id);
  assert.deepEqual(homePair(undefined), [...DEFAULT_PAIR]);
  for (const id of homePair(undefined)) assert.ok(ids.includes(id), id);
  // A fitted or unknown proposal in ?vs= falls back to the default; a candidate is taken.
  assert.deepEqual(homePair("corporate-28pct"), [...DEFAULT_PAIR]);
  assert.deepEqual(homePair("nope"), [...DEFAULT_PAIR]);
  assert.deepEqual(homePair("medicare-surcharge-2pp"), [DEFAULT_PAIR[0], "medicare-surcharge-2pp"]);
});

test("the trust strip's count is the export's held-out count", () => {
  const strip = trustStrip();
  assert.equal(strip.count, evidence().out_of_sample.n);
  assert.ok(strip.text.startsWith(`${evidence().out_of_sample.n} held-out benchmark cases`));
  assert.match(strip.text, /accuracy varies by policy type/);
});

test("each starting point opens a page that exists", () => {
  assert.equal(STARTING_POINTS.length, 3);
  for (const start of STARTING_POINTS) {
    const path = start.href.split("?")[0];
    assert.ok(fs.existsSync(new URL(`../app${path}/page.tsx`, import.meta.url)), start.href);
    assert.match(start.question, /\?$/);
  }
});
