import { test } from "node:test";
import assert from "node:assert/strict";
import { stripMarks } from "./houses";
import { houseStrip } from "./data";
import { money } from "./format";

test("the corporate strip's dots are the exported house figures, and the model is marked", () => {
  const strip = houseStrip("corporate-28pct");
  assert.ok(strip);
  assert.ok(strip.estimates.length >= 4);
  const { marks } = stripMarks(strip);
  const model = marks.filter((mark) => mark.kind === "model");
  assert.equal(model.length, 1);
  assert.equal(model[0].value, strip.model_billions);
  const houses = marks.filter((mark) => mark.kind === "house");
  assert.deepEqual(
    houses.map((mark) => mark.value),
    strip.estimates.map((row) => row.value_billions),
  );
  // Reconstruction since the credit-factor lane: no house is a fitted target.
  assert.ok(houses.every((mark) => !mark.fitted));
  const ordered = [...marks].sort((a, b) => a.value - b.value);
  for (let i = 1; i < ordered.length; i++) assert.ok(ordered[i].left >= ordered[i - 1].left);
  assert.match(money(strip.model_billions), /\$/);
});

test("a preset with no range draws no strip", () => {
  assert.equal(houseStrip("tcja-full-extension"), null);
});
