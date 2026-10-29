import assert from "node:assert/strict";
import { test } from "node:test";
import { socialSecurity } from "./data";
import { orderIds, project, selectOption } from "./socialSecurity";

const data = socialSecurity();

test("the TypeScript ledger matches the Python ledger for current law and every option alone", () => {
  assert.equal(data.checks.length, data.provisions.length + 1);
  for (const check of data.checks) {
    const got = project(data, check.provision_ids);
    const id = check.provision_ids.join(",") || "current law";
    assert.equal(got.depletionYear, check.depletion_year, id);
    if (check.payable_at_depletion === null) assert.equal(got.payableAtDepletion, null, id);
    else assert.ok(Math.abs(got.payableAtDepletion! - check.payable_at_depletion) < 1e-9, id);
    assert.ok(Math.abs(got.computedActuarialBalance - check.computed_actuarial_balance) < 1e-9, id);
    assert.ok(Math.abs(got.changeInActuarialBalance - check.change_in_actuarial_balance) < 1e-9, id);
    assert.equal(got.trustFundRatio.length, check.trust_fund_ratio.length, id);
    got.trustFundRatio.forEach((r, i) => assert.ok(Math.abs(r - check.trust_fund_ratio[i]) < 1e-6, `${id} ${i}`));
  }
});

test("current law lands on the Trustees' published figures", () => {
  const law = project(data);
  assert.equal(law.depletionYear, data.trustees.oasdi_depletion_year);
  assert.equal(Math.round(law.payableAtDepletion! * 100), data.trustees.oasdi_payable_pct);
  assert.equal(law.shareClosed, 0);
});

test("a second setting of the same lever replaces the first", () => {
  const grouped = data.provisions.filter((p) => p.exclusive_group === data.provisions[0].exclusive_group);
  assert.ok(grouped.length >= 2);
  let sel = selectOption(data, [], grouped[0].provision_id);
  sel = selectOption(data, sel, grouped[1].provision_id);
  assert.deepEqual(sel, [grouped[1].provision_id]);
  assert.deepEqual(selectOption(data, sel, grouped[1].provision_id), []);
  assert.deepEqual(orderIds(data, ["nope", grouped[1].provision_id, grouped[0].provision_id]), [grouped[0].provision_id]);
});
