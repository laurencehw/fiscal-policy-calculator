import { test } from "node:test";
import assert from "node:assert/strict";
import { buildCatalog } from "./data";
import { choose, covered, fromQuery, total, calculatorGap } from "./package";

const rows = buildCatalog();

test("one policy per exclusive group", () => {
  let s = choose(rows, [], "corporate-28pct");
  s = choose(rows, s, "corporate-15pct");
  assert.deepEqual(s, ["corporate-15pct"]);
});

test("a broader policy drops and covers the ones it contains", () => {
  let s = choose(rows, [], "ctc-extension");
  s = choose(rows, s, "tcja-full-extension");
  assert.deepEqual(s, ["tcja-full-extension"]);
  assert.equal(covered(rows, s).get("ctc-extension"), "tcja-full-extension");
});

test("the total is the sum of list prices", () => {
  const s = ["tcja-full-extension", "corporate-28pct"];
  const expected = rows.filter((r) => s.includes(r.build_id)).reduce((a, r) => a + r.score, 0);
  assert.equal(total(rows, s), expected);
});

test("a share link drops unknown ids and conflicts", () => {
  assert.deepEqual(fromQuery(rows, "corporate-28pct,nope,corporate-15pct"), ["corporate-15pct"]);
  assert.deepEqual(fromQuery(rows, "tcja-full-extension,ctc-extension"), ["tcja-full-extension"]);
  assert.deepEqual(fromQuery(rows, null), []);
});

test("Build flags a row when the calculator is a quarter or more from the published price", () => {
  // Trump Corporate 15%: published +$673.1B, calculator +$1,562.8B.
  assert.deepEqual(calculatorGap(673.1, 1562.8).differs, true);
  // TCJA Full Extension: published +$4,600B, calculator +$4,581.9B.
  const close = calculatorGap(4600, 4581.9);
  assert.equal(close.differs, false);
  assert.ok(close.share < 0.01);
  assert.equal(calculatorGap(-100, -125).differs, true);
  assert.equal(calculatorGap(-100, -124).differs, false);
  // Opposite signs always differ, however small the numbers.
  assert.equal(calculatorGap(11.4, -2).differs, true);
});
