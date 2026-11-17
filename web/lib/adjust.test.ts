import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { adjustable, matchingPresetId, TAILOR_SHAPES, tailorHref } from "./adjust";
import { DEFAULT_INPUT } from "./tailor";
import type { PresetFile } from "./types";

const dir = new URL("../../site_data/presets/", import.meta.url);

test("adjustable is true only for presets Tailor reproduces to within rounding", () => {
  const ids = readdirSync(dir)
    .filter((name) => name.endsWith(".json") && name !== "index.json")
    .map((name) => name.replace(/\.json$/, ""));
  const adjustableIds = ids.filter((id) => adjustable(id));
  assert.deepEqual(adjustableIds.sort(), Object.keys(TAILOR_SHAPES).sort());
  for (const [id, shape] of Object.entries(TAILOR_SHAPES)) {
    const file = JSON.parse(readFileSync(new URL(`${id}.json`, dir), "utf8")) as PresetFile;
    const gap = Math.abs(file.conventional.ten_year_deficit_impact - shape.tenYear);
    assert.ok(gap < 0.05, `${id} is ${gap.toFixed(3)} from its preset file`);
    assert.match(tailorHref(id) ?? "", /^\/tailor\?/);
  }
  assert.equal(adjustable("corporate-15pct"), false);
  assert.equal(adjustable("tcja-full-extension"), false);
  assert.equal(tailorHref("tcja-full-extension"), null);
});

test("Tailor's default input is the Biden 39.6% shape", () => {
  assert.equal(matchingPresetId(DEFAULT_INPUT), "top-rate-39-6");
  assert.equal(matchingPresetId({ kind: "corporate", rate: 7, who: 0, duration: 10 }), "corporate-28pct");
  assert.equal(matchingPresetId({ ...DEFAULT_INPUT, rate: 2.5 }), null);
});
