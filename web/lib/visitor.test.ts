import { test } from "node:test";
import assert from "node:assert/strict";
import { firstForwardedAddress, visitorId, visitorIdFromHeaders, visitorSalt } from "./visitor";

// The engine accepts X-Fiscal-Visitor only if it matches this (api_security.py).
const ENGINE_PATTERN = /^[A-Za-z0-9_-]{8,64}$/;

test("the first forwarded address is the visitor's", () => {
  assert.equal(firstForwardedAddress("203.0.113.5, 10.0.0.1", null), "203.0.113.5");
  assert.equal(firstForwardedAddress(null, "198.51.100.2"), "198.51.100.2");
  assert.equal(firstForwardedAddress(null, null), "unknown");
});

test("visitor ids are stable per address, salt and day, and differ otherwise", () => {
  const a = visitorId("203.0.113.5", "salt", "2026-11-23");
  assert.match(a, ENGINE_PATTERN);
  assert.equal(a, visitorId("203.0.113.5", "salt", "2026-11-23"));
  assert.notEqual(a, visitorId("203.0.113.6", "salt", "2026-11-23"));
  assert.notEqual(a, visitorId("203.0.113.5", "other", "2026-11-23"));
  assert.notEqual(a, visitorId("203.0.113.5", "salt", "2026-11-24"));
  assert.ok(!a.includes("203"), "the address must not appear in the id");
});

test("the id is read from X-Forwarded-For", () => {
  const h = new Headers({ "x-forwarded-for": "203.0.113.5, 10.0.0.1" });
  assert.equal(visitorIdFromHeaders(h, "salt"), visitorId("203.0.113.5", "salt"));
});

test("the salt comes from FISCAL_VISITOR_SALT, else one random salt per process", () => {
  assert.equal(visitorSalt({ FISCAL_VISITOR_SALT: " configured " }), "configured");
  const fallback = visitorSalt({});
  assert.match(fallback, /^[0-9a-f]{64}$/);
  assert.equal(visitorSalt({}), fallback);
  // Never another secret, never a hard-coded string.
  assert.notEqual(visitorSalt({ FISCAL_ENGINE_BYPASS: "bypass" }), "bypass");
  assert.notEqual(fallback, "fiscal-calculator");
});
