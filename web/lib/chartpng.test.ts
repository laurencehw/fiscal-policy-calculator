import { test } from "node:test";
import assert from "node:assert/strict";
import { FOOT_LINE, PNG_PAD, TITLE_LINE, pngFileName, pngLayout, pngText, wrapText } from "./chartpng";
import { estimateIdentity, identityLine } from "./identity";

const credibility = {
  own_row_tier: "out_of_sample",
  own_row_tier_label: "Out-of-sample prediction",
  n_tier1_rows: 11,
  limitations: [],
} as never;

test("a downloaded chart's footer is the long tag: producer, window and baseline", () => {
  const identity = estimateIdentity(
    { budget_window: "FY2026-2035", baseline_vintage: "February 2026", credibility },
    "model",
  );
  const text = pngText("Top rate 39.6%", identityLine(identity), "Fiscal Policy Calculator, fiscal.lwilsesamson.com/explore/top-rate-39-6");
  assert.equal(text.title, "Top rate 39.6%");
  const footer = text.footer.join(" ");
  assert.match(footer, /This calculator/);
  assert.match(footer, /FY2026-2035/);
  assert.match(footer, /CBO Feb 2026 baseline/);
  assert.match(footer, /Out-of-sample prediction/);
  assert.match(footer, /fiscal\.lwilsesamson\.com/);
});

test("the caption wraps instead of running off a phone", () => {
  const lines = wrapText("one two three four", 8, (sample) => sample.length);
  assert.deepEqual(lines, ["one two", "three", "four"]);
});

test("the header and footer are sized from the wrapped lines, not a fixed count", () => {
  const measure = (sample: string) => sample.length * 10;
  const short = pngLayout(pngText("Short", "One line", ""), 600, 200, measure, measure);
  assert.equal(short.titleLines.length, 1);
  assert.equal(short.header, 2 * PNG_PAD + TITLE_LINE);
  assert.equal(short.footer, 2 * PNG_PAD + FOOT_LINE);
  assert.equal(short.height, short.header + 200 + short.footer);
  // At phone width the same words wrap, and the canvas grows with them.
  const long = "A long proposal title that will not fit on one line of a phone-width chart";
  const narrow = pngLayout(pngText(long, "This calculator · conventional · FY2026-2035 · CBO Feb 2026 baseline", "site"), 200, 200, measure, measure);
  assert.ok(narrow.titleLines.length > 2);
  assert.equal(narrow.header, 2 * PNG_PAD + narrow.titleLines.length * TITLE_LINE);
  assert.equal(narrow.footer, 2 * PNG_PAD + narrow.footLines.length * FOOT_LINE);
  for (const line of [...narrow.titleLines, ...narrow.footLines]) {
    assert.ok(measure(line) <= 200 - 2 * PNG_PAD || !line.includes(" "), line);
  }
});

test("a file name never comes out empty", () => {
  assert.equal(pngFileName("Top rate: 39.6%"), "top-rate-39-6.png");
  assert.equal(pngFileName("!!!"), "chart.png");
});
