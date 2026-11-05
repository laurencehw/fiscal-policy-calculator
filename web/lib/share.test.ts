import { test } from "node:test";
import assert from "node:assert/strict";
import { citation, linkVersion, longDate, staleNotice, withVersion } from "./share";
import { estimateIdentity } from "./identity";

test("every link carries v=, whatever it already holds", () => {
  assert.equal(withVersion("/explore/a", "2026-11-05"), "/explore/a?v=2026-11-05");
  assert.equal(withVersion("/compare?ids=a,b", "2026-11-05"), "/compare?ids=a,b&v=2026-11-05");
  assert.equal(withVersion("/build?policies=a&v=2026-01-01#exports", "2026-11-05"), "/build?policies=a&v=2026-11-05#exports");
  assert.equal(withVersion("https://x.org/tailor?rate=2", "2026-11-05"), "https://x.org/tailor?rate=2&v=2026-11-05");
  // No scores date, no stamp.
  assert.equal(withVersion("/explore/a", ""), "/explore/a");
});

test("a link with an old v gets the recomputed notice; a current one does not", () => {
  assert.equal(staleNotice("2026-11-05", "2026-11-05"), null);
  assert.equal(staleNotice("", "2026-11-05"), null);
  const notice = staleNotice("2026-10-01", "2026-11-05");
  assert.ok(notice);
  assert.match(notice, /1 October 2026/);
  assert.match(notice, /5 November 2026/);
  assert.match(notice, /recomputed/);
  // A v that is not a date is ignored rather than trusted.
  assert.equal(linkVersion("<script>"), "");
  assert.equal(linkVersion(["2026-10-01", "x"]), "2026-10-01");
  assert.equal(longDate("2026-01-09"), "9 January 2026");
});

test("the citation says what the tag says, and links with v=", () => {
  const identity = estimateIdentity({ budget_window: "FY2026-2035", baseline_vintage: "February 2026", credibility: null }, "model");
  const cite = citation({ title: "Top rate 39.6%", identity, path: "/explore/top-rate-39-6", scoresDate: "2026-11-05", site: "https://fiscal.lwilsesamson.com" });
  assert.match(cite.text, /^Wilse-Samson, Laurence\. "Top rate 39\.6%\." Fiscal Policy Calculator\./);
  assert.match(cite.text, /This calculator · conventional · FY2026-2035 · CBO Feb 2026 baseline/);
  assert.match(cite.text, /Figures dated 5 November 2026\./);
  assert.ok(cite.text.endsWith("https://fiscal.lwilsesamson.com/explore/top-rate-39-6?v=2026-11-05"));
  const pkg = citation({ title: "A package", identity: estimateIdentity({}, "package-sum"), path: "/build?policies=a,b", scoresDate: "2026-11-05", site: "https://x.org" });
  assert.match(pkg.text, /sum of standalone published scores/);
});
