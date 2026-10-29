import { test } from "node:test";
import assert from "node:assert/strict";
import { buildCatalog, evidence, scorecardEntries, tierOf, manifest, preset, presets, presetsByArea, scoreSchema, trackerGroups, trackerIndex, views, yearCsv } from "./data";

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

test("the tracker groups hold every bill with an estimate, once", () => {
  const index = trackerIndex();
  assert.equal(index.rows.length, index.bills);
  assert.equal(index.bills, manifest().tracker_bills);
  const { cbo, auto, autoLow } = trackerGroups(index);
  assert.equal(cbo.length, index.with_cbo_estimate);
  const ids = [...cbo, ...auto, ...autoLow].map((r) => r.id);
  assert.equal(new Set(ids).size, ids.length);
  const expected = index.rows.filter((r) => r.cbo_ten_year_billions !== null || r.auto_ten_year_billions !== null);
  assert.equal(ids.length, expected.length);
  assert.ok(auto.every((r) => r.auto_confidence === "high" || r.auto_confidence === "medium"));
  for (let i = 1; i < cbo.length; i++) {
    assert.ok(Math.abs(cbo[i - 1].cbo_ten_year_billions!) >= Math.abs(cbo[i].cbo_ten_year_billions!));
  }
});

test("the scorecard splits into the tiers the evidence report counts", () => {
  const ev = evidence();
  const count = (tier: string) => scorecardEntries().filter((e) => tierOf(e) === tier).length;
  assert.equal(count("out_of_sample"), ev.out_of_sample.n);
  assert.equal(count("fitted"), ev.calibrated.fitted.n);
  assert.equal(count("reconstruction"), ev.calibrated.reconstruction.n);
  assert.equal(count("retired"), ev.calibrated.retired_targets.n);
  const mean = (tier: string) => {
    const rows = scorecardEntries().filter((e) => tierOf(e) === tier);
    return rows.reduce((s, e) => s + e.abs_percent_difference, 0) / rows.length;
  };
  assert.ok(Math.abs(mean("out_of_sample") - ev.out_of_sample.mean_abs_error) < 0.05);
  assert.ok(Math.abs(mean("fitted") - ev.calibrated.fitted.mean_abs_error) < 0.05);
  assert.ok(Math.abs(mean("reconstruction") - ev.calibrated.reconstruction.mean_abs_error) < 0.05);
});

test("every philosophy's package loads whole into the Build list", async () => {
  const { valuesArchetypes } = await import("./data");
  const { fromQuery } = await import("./package");
  const rows = buildCatalog();
  const archetypes = valuesArchetypes();
  assert.equal(archetypes.length, manifest().values_archetypes);
  for (const a of archetypes) {
    const ids = a.picks.map((p) => p.policy_id);
    assert.ok(ids.length > 0, a.id);
    assert.deepEqual([...fromQuery(rows, ids.join(","))].sort(), [...ids].sort(), a.id);
  }
});

test("every preset has who-pays and economic views", () => {
  let tables = 0;
  for (const info of presets()) {
    const v = views(info.id);
    assert.ok(v, info.id);
    if (v.distribution.available) {
      tables += 1;
      const q = v.distribution.groupings.quintile;
      assert.ok(q && q.groups.length === 5, info.id);
    }
    if (v.economic.available) {
      const d = preset(info.id)!.dynamic;
      assert.ok(Math.abs(v.economic.dynamic_total_billions - (d.dynamic_adjusted_impact ?? NaN)) < 0.01, info.id);
    }
  }
  assert.ok(tables > 10);
});
