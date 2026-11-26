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
  assert.equal(body.elasticity, 0.25);
  assert.equal(body.policy_type, "income_tax");
  assert.equal(body.dynamic, true);
});

test("eti round-trips when non-default, validates bounds, and passes to engine", () => {
  const custom = { kind: "income" as const, rate: 2.6, who: 400_000, duration: 10, dynamic: false, eti: 0.4 };
  const qs = toQuery(custom);
  assert.match(qs, /eti=0\.4/);
  assert.deepEqual(fromQuery(new URLSearchParams(qs)).input, custom);
  assert.equal(engineRequest(custom).elasticity, 0.4);
  assert.equal(typeof validate({ kind: "income", rate: 1, who: 0, duration: 10, eti: 1.5 }), "string");
  assert.equal(typeof validate({ kind: "income", rate: 1, who: 0, duration: 10, eti: -0.1 }), "string");
  const valid = validate({ kind: "income", rate: 1, who: 0, duration: 10, eti: 0 });
  assert.deepEqual(valid, { kind: "income", rate: 1, who: 0, duration: 10, dynamic: false, eti: 0 });
});

test("capital gains is a kind with a threshold and no ETI", () => {
  const input = { kind: "capital_gains" as const, rate: 2, who: 1_000_000, duration: 10, dynamic: false };
  assert.equal(toQuery(input), "type=capital_gains&rate=2&who=top1m&duration=10&dynamic=0&run=1");
  assert.deepEqual(fromQuery(new URLSearchParams(toQuery(input))).input, input);
  assert.equal(fromQuery(new URLSearchParams("type=capital_gains&eti=0.5")).input.eti, undefined);
  assert.deepEqual(validate({ kind: "capital_gains", rate: 2, who: 0, duration: 10 }), {
    kind: "capital_gains",
    rate: 2,
    who: 0,
    duration: 10,
    dynamic: false,
  });
  const body = engineRequest(input);
  assert.equal(body.policy_type, "capital_gains_tax");
  assert.equal(body.income_threshold, 1_000_000);
  assert.equal(body.rate_change, 0.02);
});

