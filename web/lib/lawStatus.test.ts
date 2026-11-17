import { test } from "node:test";
import assert from "node:assert/strict";
import { baselineEyebrow, chipText, chipWorthy } from "./lawStatus";
import type { LawStatus } from "./types";

const superseded: LawStatus = { status: "superseded", label: "Superseded by later law", note: "n", pre_2025_law: true, as_of: "2026-11-17" };
const proposed: LawStatus = { status: "proposed", label: "Proposed — not enacted", note: "n", pre_2025_law: false, as_of: "2026-11-17" };

test("a superseded preset is never labelled with the current baseline", () => {
  const line = baselineEyebrow("FY2026-2035", "February 2026", superseded);
  assert.match(line, /pre-2025 law/);
  assert.match(line, /not the CBO February 2026 baseline/);
  assert.equal(baselineEyebrow("FY2026-2035", "February 2026", proposed), "FY2026-2035 · CBO February 2026 baseline");
  assert.equal(baselineEyebrow("FY2026-2035", "February 2026", null), "FY2026-2035 · CBO February 2026 baseline");
});

test("lists chip every status but proposed", () => {
  assert.equal(chipWorthy(superseded), true);
  assert.equal(chipWorthy(proposed), false);
  assert.equal(chipWorthy(null), false);
  assert.equal(chipText(superseded), "Superseded by P.L. 119-21");
  assert.equal(chipText({ ...superseded, status: "partially" }), "Scored against pre-2025 law");
  assert.equal(chipText({ ...superseded, status: "enacted", pre_2025_law: false }), "Already law");
});

test("a partial status not tied to the 2025 law does not name it", () => {
  const tariff: LawStatus = { status: "partially", label: "Partially overtaken by later law", note: "executive order", pre_2025_law: false, as_of: "2026-11-17" };
  assert.doesNotMatch(chipText(tariff), /119-21/);
});
