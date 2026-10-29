import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { homeRowLine, homeSectionText, WORKED_PRESET_IDS, workedRows } from "./home";
import { money } from "./format";
import { preset, presets } from "./data";
import { contactText, privacyText } from "./legal";

test("the homepage section names both figures and reads them from the export", () => {
  const text = homeSectionText();
  assert.ok(text.length >= 500, `section is ${text.length} characters`);
  assert.match(text, /conventional ten-year estimate/);
  assert.match(text, /published list price/);
  for (const id of WORKED_PRESET_IDS) {
    const info = presets().find((row) => row.id === id);
    const file = preset(id);
    assert.ok(info && file && info.cbo_score !== null, id);
    const line = homeRowLine(workedRows().find((row) => row.id === id)!);
    assert.ok(text.includes(line), id);
    assert.ok(line.includes(money(file.conventional.ten_year_deficit_impact)), id);
    assert.ok(line.includes(money(info.cbo_score)), id);
  }
});

test("the homepage does not hardcode a dollar figure", () => {
  for (const file of ["home.ts", "../app/page.tsx"]) {
    const source = fs.readFileSync(new URL(file, import.meta.url), "utf8");
    assert.doesNotMatch(source, /\$[0-9]/, file);
    assert.doesNotMatch(source, /\b2700\b/, file);
    assert.doesNotMatch(source, /\b1426\.8\b/, file);
  }
});

test("contact and privacy are real pages, with no street address", () => {
  assert.ok(contactText().length >= 500, `contact is ${contactText().length}`);
  assert.ok(privacyText().length >= 500, `privacy is ${privacyText().length}`);
  assert.match(contactText(), /lw3387@nyu\.edu/);
  assert.match(privacyText(), /Anthropic/);
  assert.match(privacyText(), /not stored/);
  assert.doesNotMatch(`${contactText()} ${privacyText()}`, /streetAddress|PostalAddress|\d{5}(?:-\d{4})?/);
});

test("Explore labels a figure published only when the export says it is", () => {
  const unpublished = presets()
    .filter((row) => row.cbo_score !== null && !row.cbo_published)
    .map((row) => row.id)
    .sort();
  assert.deepEqual(unpublished, [
    "carbon-tax-50",
    "drug-negotiation-expand",
    "drug-reference-pricing",
    "tcja-extension-no-salt-cap",
  ]);
  const source = fs.readFileSync(new URL("../components/PresetList.tsx", import.meta.url), "utf8");
  assert.match(source, /cbo_published/);
});
