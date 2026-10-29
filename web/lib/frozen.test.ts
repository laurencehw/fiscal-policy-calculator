import assert from "node:assert/strict";
import { test } from "node:test";
import { frozenFrom, frozenQuery, frozenRefusal, vintageToken } from "./frozen";

test("vintage tokens match the Streamlit app's", () => {
  assert.equal(vintageToken("February 2026"), "february2026");
  assert.equal(vintageToken("CBO Feb 2026"), "feb2026");
});

test("a frozen link is read, and refused on another baseline", () => {
  const f = frozenFrom(new URLSearchParams("type=income&rate=2.6&frozen=1&baseline=february2026"));
  assert.deepEqual(f, { frozen: true, baseline: "february2026" });
  assert.equal(frozenRefusal(f, "February 2026"), null);
  assert.match(frozenRefusal(f, "January 2027") ?? "", /different baseline/);
  assert.match(frozenRefusal(frozenFrom(new URLSearchParams("frozen=1")), "February 2026") ?? "", /names no baseline/);
  assert.deepEqual(frozenFrom(new URLSearchParams("rate=1")), { frozen: false });
  assert.equal(frozenRefusal({ frozen: false }, "anything"), null);
});

test("the emitted link carries the lock and drops the instructor switch", () => {
  const q = new URLSearchParams(frozenQuery("type=income&rate=2.6&run=1&classroom=1", "February 2026"));
  assert.equal(q.get("frozen"), "1");
  assert.equal(q.get("baseline"), "february2026");
  assert.equal(q.get("classroom"), null);
  assert.equal(q.get("rate"), "2.6");
});
