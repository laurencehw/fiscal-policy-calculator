import { test } from "node:test";
import assert from "node:assert/strict";
import { OLG_SLIDERS, olgFromQuery, olgToQuery, validateOlg } from "./olg";

test("validateOlg turns percents into the engine's fractions", () => {
  assert.deepEqual(validateOlg({ capital_tax_rate: 35, payroll_tax_rate: 12.4, replacement_rate: 40 }), {
    capital_tax_rate: 0.35,
    payroll_tax_rate: 0.124,
    replacement_rate: 0.4,
  });
});

test("validateOlg refuses values outside the sliders", () => {
  assert.match(String(validateOlg({ capital_tax_rate: 70, payroll_tax_rate: 12.4, replacement_rate: 40 })), /between 5 and 60/);
  assert.match(String(validateOlg({ capital_tax_rate: "30", payroll_tax_rate: 12.4, replacement_rate: 40 })), /must be a number/);
  assert.match(String(validateOlg(null)), /JSON object/);
});

test("the /generations link round-trips and clamps", () => {
  const values = { capital_tax_rate: 35, payroll_tax_rate: 15, replacement_rate: 50 };
  assert.deepEqual(olgFromQuery(new URLSearchParams(olgToQuery(values))), values);
  const odd = olgFromQuery(new URLSearchParams("capital=99&payroll=x"));
  assert.equal(odd.capital_tax_rate, 60);
  assert.equal(odd.payroll_tax_rate, OLG_SLIDERS[1].base);
});
