import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { checkedSentence, displayedGapPct, yearRows } from "./scoreparts";
import type { Credibility, PresetFile } from "./types";

const corp = JSON.parse(readFileSync(new URL("../../site_data/presets/corporate-28pct.json", import.meta.url), "utf8")) as PresetFile;

test("year table columns add across in the deficit convention", () => {
  for (const row of yearRows(corp.conventional, corp.dynamic)) {
    assert.ok(row.dynamic !== null && row.debtService !== null);
    assert.ok(Math.abs(row.conventional + row.macro + row.debtService - row.dynamic) < 1e-6, `FY${row.year}`);
  }
  // A tax rise lowers output, so macro feedback adds to the deficit: positive.
  assert.ok(yearRows(corp.conventional, corp.dynamic)[0].macro > 0);
});

test("the gap sentence names which figure the scorecard error belongs to", () => {
  const cred = corp.conventional.credibility as Credibility;
  const point = corp.conventional.ten_year_deficit_impact;
  assert.ok(Math.abs(displayedGapPct(point, -1347) - 2.68) < 0.05);
  const text = checkedSentence(cred, point, corp.conventional.budget_window);
  assert.doesNotMatch(text, /this estimate is 4\.0% away/);
  assert.match(text, /own window and terms/);
  assert.match(text, /4\.0% away/);
  assert.match(text, /2\.7% from the published number/);
});

test("when the page figure is the scorecard figure, the short sentence stands", () => {
  const cred = { own_row_official_billions: -100, own_row_abs_pct_error: 5, own_row_tier_label: "Out-of-sample" } as Credibility;
  assert.equal(checkedSentence(cred, -95, "FY2026-2035"), "Published score -$100.0B; this estimate is 5.0% away (out-of-sample).");
  const none = { own_row_official_billions: null } as Credibility;
  assert.equal(checkedSentence(none, -95, "FY2026-2035"), "No published score for this exact policy is on file.");
});
