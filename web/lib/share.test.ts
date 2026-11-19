import { test } from "node:test";
import assert from "node:assert/strict";
import { bibtexEscape, citation, citationKey, citationStem, linkVersion, longDate, staleNotice, withVersion } from "./share";
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

test("BibTeX and RIS carry the same title, link, date and tag as the one-line citation", () => {
  const identity = estimateIdentity({ budget_window: "FY2026-2035", baseline_vintage: "February 2026", credibility: null }, "model");
  const cite = citation({ title: "Top Rate to 45%", identity, path: "/explore/top-rate-45", scoresDate: "2026-11-19", site: "https://fiscal.lwilsesamson.com" });
  const url = "https://fiscal.lwilsesamson.com/explore/top-rate-45?v=2026-11-19";
  assert.equal(cite.fileStem, "top-rate-to-45");

  // BibTeX: an @misc entry whose special characters compile.
  assert.ok(cite.bibtex.startsWith("@misc{wilsesamson2026toprate45,\n"));
  assert.match(cite.bibtex, /author = \{Wilse-Samson, Laurence\}/);
  assert.match(cite.bibtex, /title = \{\{Top Rate to 45\\%\}\}/);
  assert.match(cite.bibtex, /year = \{2026\},\n  month = nov,\n  date = \{2026-11-19\}/);
  assert.ok(cite.bibtex.includes(`url = {${url}}`));
  assert.match(cite.bibtex, /note = \{This calculator · conventional · FY2026-2035 · CBO Feb 2026 baseline\. Figures dated 19 November 2026\.\}/);
  assert.ok(!cite.bibtex.includes("doi"));
  // Braces balance, so the entry parses.
  const opens = (cite.bibtex.match(/(?<!\\)\{/g) ?? []).length;
  const closes = (cite.bibtex.match(/(?<!\\)\}/g) ?? []).length;
  assert.equal(opens, closes);

  // RIS: tagged lines, CRLF, closed by ER.
  const lines = cite.ris.split("\r\n");
  assert.deepEqual(lines.slice(0, 7), [
    "TY  - ELEC",
    "AU  - Wilse-Samson, Laurence",
    "TI  - Top Rate to 45%",
    "T2  - Fiscal Policy Calculator",
    "PY  - 2026",
    "DA  - 2026/11/19",
    `UR  - ${url}`,
  ]);
  assert.match(lines[7], /^N1  - This calculator · conventional/);
  assert.equal(lines[8], "ER  - ");
  assert.equal(lines[9], "");
  assert.ok(!cite.ris.includes("\n\n"));
});

test("a DOI, when given, appears in all three forms", () => {
  const identity = estimateIdentity({}, "package-sum");
  const cite = citation({ title: "A package", identity, path: "/build?policies=a,b", scoresDate: "2026-11-19", site: "https://x.org", doi: "10.5281/zenodo.123" });
  assert.match(cite.text, /doi:10\.5281\/zenodo\.123\. https:\/\/x\.org/);
  assert.match(cite.bibtex, /doi = \{10\.5281\/zenodo\.123\}/);
  assert.match(cite.ris, /\r\nDO  - 10\.5281\/zenodo\.123\r\n/);
});

test("no scores date: no year in the entry, and a key that says so", () => {
  const identity = estimateIdentity({}, "model");
  const cite = citation({ title: "X", identity, path: "/x", scoresDate: "", site: "https://x.org" });
  assert.ok(!/year =/.test(cite.bibtex));
  assert.ok(!/PY  -/.test(cite.ris));
  assert.equal(citationKey("Wilse-Samson, Laurence", "Comparison of Top Rate; Ünïcode", ""), "wilsesamsonndcomparisontoprate");
});

test("escaping and file names", () => {
  assert.equal(bibtexEscape("50% & $5 #1 a_b {c} ~ ^ \\"), "50\\% \\& \\$5 \\#1 a\\_b \\{c\\} \\textasciitilde{} \\textasciicircum{} \\textbackslash{}");
  assert.equal(citationStem("Comparison of Top Rate to 39.6%; Top Rate to 45%"), "comparison-of-top-rate-to-39-6-top-rate-to-45");
  assert.equal(citationStem("%%%"), "citation");
  assert.ok(citationStem("x".repeat(100)).length <= 60);
});
