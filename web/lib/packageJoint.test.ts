import { test } from "node:test";
import assert from "node:assert/strict";
import { buildCatalog, packageJoint, preset } from "./data";
import { total } from "./package";
import { calculatorTotal, interactionNotes, tierSentence } from "./packageJoint";

const rows = buildCatalog();
const joint = packageJoint();
const calculator: Record<string, number> = {};
const tiers: Record<string, string> = {};
for (const r of rows) {
  const c = preset(r.build_id)?.conventional;
  if (c && typeof c.ten_year_deficit_impact === "number") {
    calculator[r.build_id] = c.ten_year_deficit_impact;
    tiers[r.build_id] = c.credibility?.own_row_tier ?? "none";
  }
}

test("supported set: the measured overlap is applied and nothing is left out", () => {
  const s = ["top-rate-39-6", "salt-cap-repeal"];
  const t = calculatorTotal(rows, s, calculator, joint, tiers);
  assert.ok(t);
  assert.deepEqual(t.excluded, []);
  assert.equal(t.overlaps.length, 1);
  const o = t.overlaps[0];
  assert.equal(o.reference, "top-rate-39-6");
  assert.ok(o.share < 0, "less revenue together than apart");
  assert.ok(o.billions > 0, "so the deficit is higher");
  assert.equal(t.value, calculator["top-rate-39-6"] + calculator["salt-cap-repeal"] + o.billions);
  // The pre-registered figures: list-price sum +$923.1B, calculator total +$481.2B,
  // and +$546.7B since lane SSG moved the 39.6% preset's calculator score.
  assert.equal(Math.round(total(rows, s) * 10) / 10, 923.1);
  assert.equal(Math.round(t.value * 10) / 10, 546.7);
  const notes = interactionNotes(rows, s, joint);
  assert.equal(notes.length, 1);
  assert.match(notes[0], /about 16% of what .* raises alone/);
  assert.doesNotMatch(notes.join(" "), /not modelled/);
});

test("all three microsim rows: the triple adds the childless EITC with no further overlap", () => {
  const s = ["top-rate-39-6", "salt-cap-repeal", "eitc-childless-expansion"];
  const t = calculatorTotal(rows, s, calculator, joint, tiers);
  assert.ok(t);
  assert.equal(t.overlaps.length, 1);
  assert.equal(Math.round(total(rows, s) * 10) / 10, 1085.7);
  assert.equal(Math.round(t.value * 10) / 10, 724.7);
  const text = interactionNotes(rows, s, joint).join(" ");
  // Rate x credit is additive by construction, never "no interaction".
  assert.match(text, /add by construction in this model/);
  assert.match(text, /not a measurement of zero/);
  assert.doesNotMatch(text, /no interaction/i);
});

test("unsupported set: two corporate rows are summed and the shared base is named", () => {
  const s = ["corporate-28pct", "gilti-reform"];
  const t = calculatorTotal(rows, s, calculator, joint, tiers);
  assert.ok(t);
  assert.deepEqual(t.overlaps, []);
  assert.equal(t.value, calculator["corporate-28pct"] + calculator["gilti-reform"]);
  const text = interactionNotes(rows, s, joint).join(" ");
  assert.match(text, /the corporate tax base/);
  assert.match(text, /no joint model/);
});

test("mixed set: a score-only row is named as left out with its list price", () => {
  const s = ["top-rate-39-6", "tips-deduction-permanent"];
  assert.equal(calculator["tips-deduction-permanent"], undefined);
  const t = calculatorTotal(rows, s, calculator, joint, tiers);
  assert.ok(t);
  assert.deepEqual(t.scored, ["top-rate-39-6"]);
  assert.equal(t.excluded.length, 1);
  assert.equal(t.excluded[0].id, "tips-deduction-permanent");
  assert.equal(t.value, calculator["top-rate-39-6"]);
  assert.match(interactionNotes(rows, s, joint).join(" "), /not modelled/);
});

test("nothing to show under two policies or when none is scored", () => {
  assert.equal(calculatorTotal(rows, ["top-rate-39-6"], calculator, joint, tiers), null);
  assert.equal(calculatorTotal(rows, ["tips-deduction-permanent", "overtime-deduction-permanent"], calculator, joint, tiers), null);
  assert.deepEqual(interactionNotes(rows, ["top-rate-39-6"], joint), []);
});

test("the tier sentence names every tier it mixes", () => {
  assert.equal(tierSentence({ fitted: 2 }), "Both are calibrated to their published figures.");
  assert.equal(
    tierSentence({ reconstruction: 3, out_of_sample: 1 }),
    "Mixes tiers: 1 out-of-sample prediction, 3 unfitted reconstructions.",
  );
  assert.equal(tierSentence({ reconstruction: 1 }), "The one I score is an unfitted reconstruction.");
});

test("every catalog row has an interaction channel entry", () => {
  for (const r of rows) assert.ok(r.build_id in joint.channels, r.build_id);
});
