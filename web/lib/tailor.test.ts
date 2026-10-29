import { test } from "node:test";
import assert from "node:assert/strict";
import { DEFAULT_INPUT, engineRequest, fromQuery, parseWho, toQuery, validate } from "./tailor";

test("who reads the app's spellings", () => {
  assert.equal(parseWho("top400k"), 400_000);
  assert.equal(parseWho("400k"), 400_000);
  assert.equal(parseWho("$1M"), 1_000_000);
  assert.equal(parseWho("275000"), 275_000);
  assert.equal(parseWho("millionaires"), 1_000_000);
  assert.equal(parseWho("nonsense"), null);
  assert.equal(parseWho("20m"), null);
});

test("a link round-trips", () => {
  const input = { kind: "income" as const, rate: 2.6, who: 400_000, duration: 10, dynamic: true };
  const back = fromQuery(new URLSearchParams(toQuery(input)));
  assert.deepEqual(back.input, input);
  assert.equal(back.run, true);
  assert.equal(toQuery(input), "type=income&rate=2.6&who=top400k&duration=10&dynamic=1&run=1");
});

test("bad parameters keep their defaults and out-of-range ones are clamped", () => {
  const { input, run } = fromQuery(new URLSearchParams("rate=nan&who=x&duration=40&type=spending"));
  assert.deepEqual(input, { ...DEFAULT_INPUT, duration: 10 });
  assert.equal(run, false);
  assert.equal(fromQuery(new URLSearchParams("rate=12")).input.rate, 10);
  assert.equal(fromQuery(new URLSearchParams("type=corporate&who=top400k")).input.who, 0);
});

test("the route refuses what the engine would", () => {
  assert.equal(typeof validate({ kind: "payroll", rate: 1, who: 0, duration: 10 }), "string");
  assert.equal(typeof validate({ kind: "income", rate: 11, who: 0, duration: 10 }), "string");
  assert.equal(typeof validate({ kind: "income", rate: 0, who: 0, duration: 10 }), "string");
  assert.equal(typeof validate({ kind: "corporate", rate: 7, who: 400000, duration: 10 }), "string");
  assert.equal(typeof validate({ kind: "income", rate: 1, who: 0, duration: 2.5 }), "string");
  assert.deepEqual(validate({ kind: "corporate", rate: 7, who: 0, duration: 10 }), {
    kind: "corporate",
    rate: 7,
    who: 0,
    duration: 10,
    dynamic: false,
  });
});

test("points become the engine's decimal fraction", () => {
  const body = engineRequest({ kind: "income", rate: 2.6, who: 400_000, duration: 10, dynamic: false });
  assert.equal(body.rate_change, 0.026);
  assert.equal(body.income_threshold, 400_000);
  assert.equal(body.policy_type, "income_tax");
  assert.equal(body.dynamic, true);
});
