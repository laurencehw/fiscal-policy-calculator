import { test } from "node:test";
import assert from "node:assert/strict";
import { cleanLabel, direction, dollars, money, shortLabel } from "./format";

test("money carries a sign and one decimal", () => {
  assert.equal(money(4581.937589), "+$4,581.9B");
  assert.equal(money(-302.23), "-$302.2B");
  assert.equal(money(0), "$0.0B");
  assert.equal(money(4581.9, { trillions: true }), "+$4.58T");
  assert.equal(money(-850, { trillions: true }), "-$850.0B");
});

test("direction reads the deficit convention", () => {
  assert.equal(direction(10), "adds to the deficit");
  assert.equal(direction(-10), "reduces the deficit");
});

test("labels lose the emoji and the Markdown escapes", () => {
  assert.equal(cleanLabel("🏛️ TCJA Full Extension (CBO: $4.6T)"), "TCJA Full Extension (CBO: $4.6T)");
  assert.equal(shortLabel("🏛️ TCJA Full Extension (CBO: $4.6T)"), "TCJA Full Extension");
  assert.equal(cleanLabel("Repeal the \\$10K SALT cap"), "Repeal the $10K SALT cap");
  assert.equal(shortLabel("📋 Repeal SALT Cap"), "Repeal SALT Cap");
});

test("dollars rounds to whole dollars with a sign", () => {
  assert.equal(dollars(28272.51), "+$28,273");
  assert.equal(dollars(-1274.4), "-$1,274");
  assert.equal(dollars(0.3), "$0");
});
