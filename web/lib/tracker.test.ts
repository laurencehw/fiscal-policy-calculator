import { test } from "node:test";
import assert from "node:assert/strict";
import { billMoney, filterBills } from "./tracker";
import { money } from "./format";
import type { TrackerRow } from "./types";

const row = (over: Partial<TrackerRow>): TrackerRow => ({ ...({} as TrackerRow), ...over });
const rows = [
  row({ id: "1", type: "hr", number: "1", title: "An act to provide for reconciliation", status: "enacted" }),
  row({ id: "2", type: "s", number: "2779", title: "Tax Cut for Striking Workers Act", status: "committee" }),
  row({ id: "3", type: "hr", number: "5810", title: "Federal Supervisor Education Act", status: "committee" }),
];

test("bills filter by number, by words in the title, and by status", () => {
  assert.deepEqual(filterBills(rows, "h.r. 5810", "").map((r) => r.id), ["3"]);
  assert.deepEqual(filterBills(rows, "s2779", "").map((r) => r.id), ["2"]);
  assert.deepEqual(filterBills(rows, "tax workers", "").map((r) => r.id), ["2"]);
  assert.deepEqual(filterBills(rows, "", "committee").map((r) => r.id), ["2", "3"]);
  assert.deepEqual(filterBills(rows, "act", "enacted").map((r) => r.id), ["1"]);
});

test("amounts that round to zero say so instead of printing a signed zero", () => {
  assert.equal(billMoney(0.04, money), "+ under $0.1B");
  assert.equal(billMoney(-0.01, money), "- under $0.1B");
  assert.equal(billMoney(0, money), "$0.0B");
  assert.equal(billMoney(3.3, money), "+$3.3B");
});
