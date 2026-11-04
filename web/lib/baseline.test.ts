import { test } from "node:test";
import assert from "node:assert/strict";
import { axisMoney, deficitPaths, pathGap, sum, trillions } from "./baseline";
import { baseline, preset } from "./data";

test("the February 2026 baseline deficit is $23.1T and the chart gap is the headline", () => {
  const file = baseline();
  const total = sum(file.years.map((row) => -row.deficit_billions));
  assert.ok(Math.abs(total - 23143.3) < 0.05, String(total));
  assert.equal(trillions(total), "$23.1T");

  const scored = preset("tcja-full-extension");
  assert.ok(scored);
  const points = deficitPaths(
    file.years,
    scored.conventional.year_by_year.map((row) => ({ year: row.year, value: row.final_effect })),
  );
  const gap = pathGap(points);
  assert.ok(Math.abs(gap - scored.conventional.ten_year_deficit_impact) < 0.01, `${gap} vs ${scored.conventional.ten_year_deficit_impact}`);
  assert.equal(points.length, scored.conventional.year_by_year.length);
});

test("axis labels stay short enough for a phone", () => {
  assert.equal(axisMoney(32095), "$32T");
  assert.equal(axisMoney(1852), "$1.9T");
  assert.equal(axisMoney(-400), "-$400B");
});
