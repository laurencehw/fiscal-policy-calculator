import { test } from "node:test";
import assert from "node:assert/strict";
import { pngCaption, wrapText } from "./chartpng";

test("a downloaded chart names the proposal, the source and the vintage", () => {
  const lines = pngCaption("TCJA Full Extension", "Fiscal Policy Calculator, conventional score", "CBO February 2026 baseline, FY2026-2035");
  assert.equal(lines[0], "TCJA Full Extension");
  assert.match(lines[1], /Fiscal Policy Calculator, conventional score/);
  assert.match(lines[1], /CBO February 2026 baseline/);
  assert.match(lines[1], /FY2026-2035/);
});

test("the caption wraps instead of running off a phone", () => {
  const lines = wrapText("one two three four", 8, (sample) => sample.length);
  assert.deepEqual(lines, ["one two", "three", "four"]);
});
