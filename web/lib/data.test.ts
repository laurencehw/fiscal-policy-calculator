import { test } from "node:test";
import assert from "node:assert/strict";
import { buildCatalog, manifest, preset, presets, presetsByArea, scoreSchema, yearCsv } from "./data";

test("every listed preset has its file, in both modes", () => {
  const list = presets();
  assert.equal(list.length, manifest().presets);
  for (const info of list) {
    const file = preset(info.id);
    assert.ok(file, info.id);
    assert.equal(file.conventional.policy_name, info.name);
    assert.equal(file.conventional.ten_year_deficit_impact, file.dynamic.ten_year_deficit_impact, info.id);
    assert.equal(file.conventional.year_by_year.length, file.dynamic.year_by_year.length, info.id);
  }
});

test("an id outside the export is not read", () => {
  assert.equal(preset("../manifest"), null);
  assert.equal(preset("no-such-preset"), null);
});

test("the fields the site reads are in the API's schema", () => {
  const schema = scoreSchema();
  for (const key of ["policy_name", "baseline_vintage", "budget_window", "ten_year_deficit_impact", "dynamic_adjusted_impact", "year_by_year", "credibility"]) {
    assert.ok(key in schema.properties, key);
  }
  for (const key of ["year", "final_effect", "dynamic_effect", "debt_service"]) {
    assert.ok(key in schema.$defs.YearlyEffect.properties, key);
  }
  for (const key of ["own_row_official_billions", "own_row_abs_pct_error", "caption", "uncertainty_low"]) {
    assert.ok(key in schema.$defs.ResultCredibilityModel.properties, key);
  }
});

test("grouping keeps every preset once", () => {
  const grouped = presetsByArea().flatMap((group) => group.presets.map((p) => p.id));
  assert.deepEqual([...grouped].sort(), presets().map((p) => p.id).sort());
  assert.ok(buildCatalog().length > 0);
  const areas = presetsByArea().map((group) => group.area);
  assert.match(areas[areas.length - 1], /^Illustrative/);
});

test("the CSV has a row per year and sums to the headline", () => {
  const file = preset("tcja-full-extension")!;
  const csv = yearCsv(file.conventional, file.dynamic).trim().split("\n");
  const rows = csv.filter((line) => /^\d{4},/.test(line));
  assert.equal(rows.length, file.conventional.year_by_year.length);
  const header = csv.find((line) => line.startsWith("year,"))!.split(",");
  const total = rows.reduce((sum, line) => sum + Number(line.split(",")[header.indexOf("final_effect")]), 0);
  assert.ok(Math.abs(total - file.conventional.ten_year_deficit_impact) < 0.01);
});
