import { test } from "node:test";
import assert from "node:assert/strict";
import { baselineEyebrow, chipText, chipWorthy, currentLawFigure, currentLawLine } from "./lawStatus";
import { preset, presets } from "./data";
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

const answer = (kind: "already_law" | "same_as" | "not_computed", same_as: string | null = null) => ({
  kind,
  billions: kind === "already_law" ? 0 : null,
  same_as,
  already_ended_billions: null,
  reason: "r",
  source: "s",
  url: "u",
});

test("a pre-2025-law preset's current-law figure follows its kind", () => {
  const lookup = (id: string) => (id === "salt-cap-repeal" ? 740.3 : null);
  assert.equal(currentLawFigure({ ...superseded, current_law: answer("already_law") }, lookup), 0);
  assert.equal(currentLawFigure({ ...superseded, current_law: answer("same_as", "salt-cap-repeal") }, lookup), 740.3);
  assert.equal(currentLawFigure({ ...superseded, current_law: answer("not_computed") }, lookup), null);
  assert.equal(currentLawFigure({ ...proposed, current_law: answer("already_law") }, lookup), null);
  assert.equal(currentLawLine({ ...superseded, current_law: answer("already_law") }, 0), "$0 on current law: already law");
  assert.equal(currentLawLine({ ...superseded, current_law: answer("not_computed") }, null), "Not scored on current law");
  assert.equal(currentLawLine(proposed, null), null);
});

test("every exported pre-2025-law preset has a current-law answer, and no-SALT-cap TCJA reads the SALT repeal score", () => {
  const read = (id: string) => preset(id)?.conventional.ten_year_deficit_impact ?? null;
  const pre = presets().filter((info) => info.status?.pre_2025_law);
  assert.ok(pre.length >= 8);
  for (const info of pre) assert.ok(info.status?.current_law, info.id);
  const noCap = presets().find((info) => info.id === "tcja-extension-no-salt-cap");
  assert.equal(currentLawFigure(noCap?.status, read), read("salt-cap-repeal"));
  const full = presets().find((info) => info.id === "tcja-full-extension");
  assert.equal(currentLawFigure(full?.status, read), 0);
});
