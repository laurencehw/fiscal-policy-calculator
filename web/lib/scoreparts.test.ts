import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { checkedSentence, conventionalFromRevenue, displayedGapPct, whoPaysReconciliation, yearRows, yearTableNote } from "./scoreparts";
import type { Credibility, PresetFile } from "./types";

const corp = JSON.parse(readFileSync(new URL("../../site_data/presets/corporate-28pct.json", import.meta.url), "utf8")) as PresetFile;
const top45 = JSON.parse(readFileSync(new URL("../../site_data/presets/top-rate-45.json", import.meta.url), "utf8")) as PresetFile;

test("year table columns add across in the deficit convention", () => {
  for (const row of yearRows(corp.conventional, corp.dynamic)) {
    assert.ok(row.dynamic !== null && row.debtService !== null);
    assert.ok(Math.abs(row.conventional + row.macro + row.debtService - row.dynamic) < 1e-6, `FY${row.year}`);
  }
  // A tax rise lowers output, so macro feedback adds to the deficit: positive.
  assert.ok(yearRows(corp.conventional, corp.dynamic)[0].macro > 0);
});

test("revenue minus the behavioral offset is the conventional deficit with the sign flipped", () => {
  const rows = yearRows(top45.conventional, top45.dynamic);
  const fy2026 = rows.find((row) => row.year === 2026);
  assert.ok(fy2026);
  assert.ok(Math.abs(fy2026.revenue - 98.6) < 0.05, `revenue ${fy2026.revenue}`);
  assert.ok(Math.abs(fy2026.behavioral - 12.3) < 0.05, `behavioral ${fy2026.behavioral}`);
  assert.ok(Math.abs(fy2026.conventional + 86.3) < 0.05, `conventional ${fy2026.conventional}`);
  for (const row of rows) {
    assert.ok(Math.abs(row.conventional - conventionalFromRevenue(row.revenue, row.behavioral)) < 1e-6, `FY${row.year}`);
  }
  assert.match(yearTableNote(), /behavioral offset/i);
  const table = readFileSync(new URL("../components/ScoreParts.tsx", import.meta.url), "utf8");
  assert.match(table, /Behavioral offset/);
});

test("the who-pays note names the first-year budget score beside the incidence total", () => {
  const first = top45.conventional.year_by_year[0];
  const text = whoPaysReconciliation(64.0, first);
  assert.match(text, /static incidence/);
  assert.match(text, /FY2026/);
  assert.match(text, /-\$86\.3B/);
  assert.doesNotMatch(text, /discrepancy|error|mismatch/i);
});

test("the gap sentence names which figure the scorecard error belongs to", () => {
  const cred = corp.conventional.credibility as Credibility;
  const point = corp.conventional.ten_year_deficit_impact;
  assert.ok(Math.abs(displayedGapPct(point, -1347) - 2.68) < 0.05);
  const text = checkedSentence(cred, point, corp.conventional.budget_window);
  assert.doesNotMatch(text, /this estimate is 4\.0% away/);
  assert.match(text, /own window \(FY2025-2034\) and terms/);
  assert.match(text, /4\.0% away/);
  assert.match(text, /2\.7% from the published number/);
});

test("when the page figure is the scorecard figure, the short sentence stands", () => {
  const cred = { own_row_official_billions: -100, own_row_abs_pct_error: 5, own_row_tier_label: "Out-of-sample" } as Credibility;
  assert.equal(checkedSentence(cred, -95, "FY2026-2035"), "Published score -$100.0B; this estimate is 5.0% away (out-of-sample).");
  const none = { own_row_official_billions: null } as Credibility;
  assert.equal(checkedSentence(none, -95, "FY2026-2035"), "No published score for this exact policy is on file.");
});
