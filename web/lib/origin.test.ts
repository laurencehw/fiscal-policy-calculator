import { test } from "node:test";
import assert from "node:assert/strict";
import { isSameOrigin } from "./origin";

const SITE = "https://fiscal.example.org";

function headers(values: Record<string, string>): Headers {
  return new Headers(values);
}

test("a request with no Origin passes", () => {
  assert.equal(isSameOrigin(headers({ host: "fiscal.example.org" }), { siteOrigin: SITE, allowLocalhost: false }), true);
});

test("an Origin matching the request's host passes, including preview deployments", () => {
  const h = headers({ origin: "https://preview-abc.vercel.app", "x-forwarded-host": "preview-abc.vercel.app" });
  assert.equal(isSameOrigin(h, { siteOrigin: SITE, allowLocalhost: false }), true);
  const plain = headers({ origin: "https://fiscal.example.org", host: "fiscal.example.org" });
  assert.equal(isSameOrigin(plain, { siteOrigin: SITE, allowLocalhost: false }), true);
});

test("the configured site origin passes even behind a different internal host", () => {
  const h = headers({ origin: SITE, host: "internal:3000" });
  assert.equal(isSameOrigin(h, { siteOrigin: SITE, allowLocalhost: false }), true);
});

test("a foreign Origin is refused", () => {
  const h = headers({ origin: "https://evil.example.com", host: "fiscal.example.org" });
  assert.equal(isSameOrigin(h, { siteOrigin: SITE, allowLocalhost: false }), false);
  // Same registrable name on another port is another origin's host too.
  const port = headers({ origin: "https://fiscal.example.org:8443", host: "fiscal.example.org" });
  assert.equal(isSameOrigin(port, { siteOrigin: SITE, allowLocalhost: false }), false);
});

test("Origin: null and garbage are refused", () => {
  assert.equal(isSameOrigin(headers({ origin: "null", host: "fiscal.example.org" }), { siteOrigin: SITE, allowLocalhost: false }), false);
  assert.equal(isSameOrigin(headers({ origin: "not a url", host: "fiscal.example.org" }), { siteOrigin: SITE, allowLocalhost: false }), false);
});

test("localhost passes only when allowed (development)", () => {
  const h = headers({ origin: "http://localhost:3000", host: "fiscal.example.org" });
  assert.equal(isSameOrigin(h, { siteOrigin: SITE, allowLocalhost: true }), true);
  assert.equal(isSameOrigin(h, { siteOrigin: SITE, allowLocalhost: false }), false);
  const loopback = headers({ origin: "http://127.0.0.1:3000", host: "fiscal.example.org" });
  assert.equal(isSameOrigin(loopback, { siteOrigin: SITE, allowLocalhost: true }), true);
});
