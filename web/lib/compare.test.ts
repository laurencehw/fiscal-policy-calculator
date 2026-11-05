import { test } from "node:test";
import assert from "node:assert/strict";
import {
  differenceNote,
  differenceYears,
  OUT_OF_SAMPLE_PRESET_IDS,
  refusedSentence,
  selectIds,
  sharedDomain,
  unknownSentence,
} from "./compare";

const known = new Set(["a", "b", "c", "d", "top-rate-39-6", "corporate-28pct"]);

test("the shared domain covers every series", () => {
  const domain = sharedDomain([
    [-10, 50],
    [5, -80],
  ]);
  assert.ok(domain.low <= -80);
  assert.ok(domain.high >= 50);
  assert.ok(domain.ticks.includes(0) || (domain.low <= 0 && domain.high >= 0));
});

test("a pair on different windows has an explanation and no difference line", () => {
  const note = differenceNote([
    { name: "One", window: "FY2026-2035", baseline: "CBO February 2026" },
    { name: "Two", window: "FY2025-2034", baseline: "CBO February 2026" },
  ]);
  assert.equal(note.draw, false);
  assert.match(note.text, /FY2025-2034/);
  assert.match(note.text, /do not draw a difference/);
  const same = differenceNote([
    { name: "One", window: "FY2026-2035", baseline: "CBO February 2026" },
    { name: "Two", window: "FY2026-2035", baseline: "CBO February 2026" },
  ]);
  assert.equal(same.draw, true);
  assert.equal(differenceYears([{ year: 2026, value: 2 }], [{ year: 2026, value: 5 }])?.[0].value, -3);
  assert.equal(differenceYears([{ year: 2026, value: 2 }], [{ year: 2027, value: 5 }]), null);
});

test("an unknown id is dropped and named, and a fourth id is refused", () => {
  const picked = selectIds("a,nope,b,c,d,a", known);
  assert.deepEqual(picked.ids, ["a", "b", "c"]);
  assert.deepEqual(picked.unknown, ["nope"]);
  assert.deepEqual(picked.refused, ["d"]);
  assert.match(unknownSentence(picked.unknown), /nope/);
  assert.match(refusedSentence(picked.refused), /d/);
  assert.match(refusedSentence(picked.refused), /three/);
});

test("the U6 pair is the out-of-sample preset, not a corporate one", () => {
  assert.deepEqual([...OUT_OF_SAMPLE_PRESET_IDS], ["top-rate-39-6"]);
  assert.equal(OUT_OF_SAMPLE_PRESET_IDS.includes("corporate-28pct" as never), false);
});
