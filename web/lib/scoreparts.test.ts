import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { checkedExtraNote, checkedSentence, displayedGapPct, hasOther, whoPaysReconciliation, yearRows } from "./scoreparts";
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
  assert.ok(Math.abs(displayedGapPct(point, -1347) - 28.08) < 0.05);
  const text = checkedSentence(cred, point, corp.conventional.budget_window);
  assert.doesNotMatch(text, /this estimate is 29\.1% away/);
  assert.match(text, /own window \(FY2025-2034\) and terms/);
  assert.match(text, /29\.1% away/);
  assert.match(text, /28\.1% from the published number/);
});

test("when the page figure is the scorecard figure, the short sentence stands", () => {
  const cred = { own_row_official_billions: -100, own_row_abs_pct_error: 5, own_row_tier_label: "Out-of-sample" } as Credibility;
  assert.equal(checkedSentence(cred, -95, "FY2026-2035"), "Published score -$100.0B; this estimate is 5.0% away (out-of-sample).");
  const none = { own_row_official_billions: null } as Credibility;
  assert.equal(checkedSentence(none, -95, "FY2026-2035"), "No published score for this exact policy is on file.");
});

test("checkedExtraNote keeps only the non-redundant qualifier after the em-dash", () => {
  const cred = {
    own_row_official_billions: -2171.1,
    own_row_caption: "Unfitted reconstruction, 36.4% from -$2.17T (Tax Foundation (Fiscal Fact 861)) — no constant is fitted to this figure.",
  } as Credibility;
  assert.equal(checkedExtraNote(cred), "No constant is fitted to this figure.");
  assert.equal(checkedExtraNote({ own_row_official_billions: null, own_row_caption: "x — y" } as Credibility), "");
});

const top45 = JSON.parse(readFileSync(new URL("../../site_data/presets/top-rate-45.json", import.meta.url), "utf8")) as PresetFile;

test("the conventional deficit is minus revenue and the behavioural response (review B6)", () => {
  for (const file of [top45, corp]) {
    const rows = yearRows(file.conventional, file.dynamic);
    assert.equal(hasOther(rows), false);
    for (const row of rows) {
      assert.ok(Math.abs(-(row.revenue + row.behavioural) - row.conventional) < 1e-6, `FY${row.year}`);
    }
  }
  // A rate rise: the response takes some of the static revenue back.
  const first = yearRows(top45.conventional, top45.dynamic)[0];
  assert.ok(first.revenue > 0 && first.behavioural < 0);
});

test("the Who pays note names both first-year figures", () => {
  const first = yearRows(top45.conventional, top45.dynamic)[0];
  const text = whoPaysReconciliation(first, 2026, 63.99);
  assert.match(text, /\+\$98\.6B before the behavioural response/);
  assert.match(text, /\+\$86\.3B after it/);
  assert.match(text, /totals \+\$64\.0B/);
});
