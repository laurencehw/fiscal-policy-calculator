import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { estimateIdentity, identityLine, shortProducer } from "./identity";
import type { Credibility, PresetFile } from "./types";

const corp = JSON.parse(readFileSync(new URL("../../site_data/presets/corporate-28pct.json", import.meta.url), "utf8")) as PresetFile;
const noRow = JSON.parse(
  readFileSync(new URL("../../site_data/presets/ultra-millionaire-surtax-3pp.json", import.meta.url), "utf8"),
) as PresetFile;

test("a fitted row's tag says calibrated and never out of sample", () => {
  const line = identityLine(estimateIdentity(corp.conventional, "model"));
  assert.match(line, /calibrated/i);
  assert.doesNotMatch(line, /out of sample/i);
  assert.match(line, /This calculator · conventional · FY2026-2035 · CBO Feb 2026 baseline/);
});

test("the corporate 28% published tag names Treasury, not CBO", () => {
  const identity = estimateIdentity({ ...corp.conventional, cbo_source: "Treasury" }, "published");
  const line = identityLine(identity);
  assert.equal(identity.producer, "Treasury");
  assert.match(line, /Treasury/);
  assert.doesNotMatch(line, /\bCBO\b/);
  assert.equal(shortProducer(identity), "Treasury");
});

test("a policy with no own row takes the class band, and none when the class has no rows", () => {
  const band = estimateIdentity(noRow.conventional, "model");
  assert.equal(band.tier, "out_of_sample");
  assert.match(band.tierLabel, /n=4/);
  const none = estimateIdentity(
    { budget_window: "FY2026-2035", baseline_vintage: "February 2026", credibility: { n_tier1_rows: 0, own_row_tier: null } as Credibility },
    "model",
  );
  assert.equal(none.tier, "none");
});

test("a package sum does not claim one baseline or one tier", () => {
  const identity = estimateIdentity(corp.conventional, "package-sum");
  assert.equal(identity.tier, "none");
  assert.equal(identity.baseline, "");
  assert.match(identity.limitation, /Interactions between these policies are not measured/);
  assert.equal(shortProducer(identity), "sum");
  assert.doesNotMatch(identityLine(identity), /\bCBO\b/);
});

test("the dynamic tag names the feedback and does not inherit the conventional tier", () => {
  const identity = estimateIdentity(corp.dynamic, "model-dynamic");
  assert.equal(identity.tier, "none");
  const line = identityLine(identity);
  assert.match(line, /with macroeconomic feedback/);
  assert.doesNotMatch(line, /calibrated/i);
  assert.match(line, /not benchmarked/);
});

test("the published tag names the producer and carries no tier label", () => {
  const index = JSON.parse(readFileSync(new URL("../../site_data/presets/index.json", import.meta.url), "utf8")) as {
    presets: { id: string; cbo_source?: string }[];
  };
  const source = index.presets.find((row) => row.id === "corporate-28pct")?.cbo_source ?? "";
  assert.match(source, /Treasury/, "the exported corporate 28% source should name Treasury");
  const line = identityLine(estimateIdentity({ ...corp.conventional, cbo_source: source }, "published"));
  assert.doesNotMatch(line, /calibrated|out-of-sample|reconstruction/i);
  assert.doesNotMatch(line, /\bCBO\b/);
});

test("a column header with no named producer does not repeat the word published", () => {
  const line = identityLine(estimateIdentity({ cbo_source: "Published", credibility: null }, "published"));
  assert.equal(line, "Published");
});
