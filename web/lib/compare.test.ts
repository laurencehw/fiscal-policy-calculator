import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  DEFAULT_PAIR,
  MAX_COMPARE,
  compareHref,
  difference,
  droppedSentences,
  parseIds,
  sharedAxis,
  toggleId,
  type CompareItem,
} from "./compare";

const known = new Set(["a", "b", "c", "d"]);

function item(id: string, values: number[], window = "FY2026-2035", baseline = "February 2026"): CompareItem {
  return {
    id,
    name: id.toUpperCase(),
    window,
    baseline,
    tenYear: values.reduce((sum, v) => sum + v, 0),
    years: values.map((value, i) => ({ year: 2026 + i, value })),
  };
}

test("ids are read in order, deduplicated, and unknown ones are dropped and named", () => {
  const parsed = parseIds("b, a,zzz,b", known);
  assert.deepEqual(parsed.ids, ["b", "a"]);
  assert.deepEqual(parsed.unknown, ["zzz"]);
  assert.deepEqual(parsed.refused, []);
  const lines = droppedSentences(parsed);
  assert.equal(lines.length, 1);
  assert.match(lines[0], /"zzz"/);
  assert.deepEqual(parseIds(["a", "c"], known).ids, ["a", "c"]);
  assert.deepEqual(parseIds(undefined, known), { ids: [], unknown: [], refused: [] });
});

test("a fourth id is refused, in the URL and in the picker", () => {
  const parsed = parseIds("a,b,c,d", known);
  assert.equal(parsed.ids.length, MAX_COMPARE);
  assert.deepEqual(parsed.refused, ["d"]);
  assert.match(droppedSentences(parsed).join(" "), /at most 3 .*"d"/);
  assert.deepEqual(toggleId(["a", "b", "c"], "d"), ["a", "b", "c"]);
  assert.deepEqual(toggleId(["a", "b", "c"], "b"), ["a", "c"]);
  assert.deepEqual(toggleId(["a"], "b"), ["a", "b"]);
  assert.equal(compareHref(["a", "b", "c", "d"]), "/compare?ids=a,b,c");
  assert.equal(compareHref([]), "/compare");
});

test("the shared axis covers every series and includes zero", () => {
  const items = [item("a", [-30, -40, -55]), item("b", [10, 120, 260]), item("c", [-5, 5])];
  const axis = sharedAxis(items);
  for (const it of items) {
    for (const row of it.years) {
      assert.ok(row.value >= axis.lo && row.value <= axis.hi, `${it.id} ${row.year} outside the axis`);
    }
  }
  assert.ok(axis.lo <= 0 && axis.hi >= 0);
  assert.deepEqual(sharedAxis([]).ticks.includes(0), true);
});

test("a pair on different windows shows the reason and no difference", () => {
  const result = difference([item("a", [1, 2]), item("b", [3, 4], "FY2025-2034")]);
  assert.equal(result.drawn, false);
  assert.ok(!result.drawn && /different windows/.test(result.reason));
  const baselines = difference([item("a", [1]), item("b", [2], "FY2026-2035", "June 2024")]);
  assert.ok(!baselines.drawn && /different baselines/.test(baselines.reason));
});

test("a pair on one window and baseline gets a difference; one or three never do", () => {
  const pair = difference([item("a", [-100, -200]), item("b", [-50, -50])]);
  assert.ok(pair.drawn);
  assert.equal(pair.drawn && pair.billions, 200);
  assert.match(pair.drawn ? pair.sentence : "", /B leaves the deficit \$200\.0B higher than A/);
  assert.match(pair.drawn ? pair.sentence : "", /not the effect of doing both/);
  assert.equal(difference([item("a", [1])]).drawn, false);
  const three = difference([item("a", [1]), item("b", [2]), item("c", [3])]);
  assert.ok(!three.drawn && /no difference or total/.test(three.reason));
});

test("the default pair names two presets that exist", () => {
  for (const id of DEFAULT_PAIR) {
    const file = new URL(`../../site_data/presets/${id}.json`, import.meta.url);
    assert.ok(fs.existsSync(file), id);
    // Both must read off the out-of-sample tier: their own pre-registered row, or the class band.
    const cred = JSON.parse(fs.readFileSync(file, "utf8")).conventional.credibility;
    assert.ok(cred.own_row_tier === "out_of_sample" || (cred.own_row_tier === null && cred.n_tier1_rows > 0), id);
  }
});
