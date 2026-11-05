import { test } from "node:test";
import assert from "node:assert/strict";
import { PACKAGE_EXCLUSION, packageCsv, packageSvg } from "./packageExport";
import type { BuildRow } from "./types";

function row(build_id: string, label: string, score: number): BuildRow {
  return { build_id, label, score, area: "A", source: "CBO", source_date: "Dec 2024", exclusive_groups: [], subsumes: [], illustrative: false };
}

const rows = [row("a", '📋 Cap, "charitable" deduction (CBO: -$200B)', -200), row("b", "Repeal SALT cap", 740.3), row("c", "Unpicked", 1)];
const colors = { ink: "#000", muted: "#555", rule: "#ccc", adds: "#b14c28", reduces: "#1f5e7a", paper: "#fff" };

test("the first line of Build's CSV is the exclusion sentence", () => {
  const csv = packageCsv(rows, ["b", "a"], { a: -174.9 }, { link: "https://x.org/build?policies=b,a&v=2026-11-05", dated: "5 November 2026" });
  const lines = csv.trim().split("\n");
  assert.equal(lines[0], `# ${PACKAGE_EXCLUSION}`);
  assert.match(PACKAGE_EXCLUSION, /interactions between these policies are not measured/);
  assert.match(lines[2], /5 November 2026/);
  // Catalog order, labels quoted where they carry commas or quotes, the total last.
  assert.equal(lines[4], 'a,"Cap, ""charitable"" deduction",-200,CBO,Dec 2024,-174.9');
  assert.equal(lines[5], "b,Repeal SALT cap,740.3,CBO,Dec 2024,");
  assert.equal(lines.at(-1), "total,Sum of the published figures above,540.3,,,");
  assert.ok(!csv.includes("Unpicked"));
});

test("the package picture draws each chosen policy and the total, escaped", () => {
  const { svg, height } = packageSvg(rows, ["a", "b"], 640, colors);
  assert.match(svg, /^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg"/);
  assert.match(svg, /Cap, &quot;charitable&quot; deduction/);
  assert.match(svg, /Repeal SALT cap/);
  assert.match(svg, /Package total/);
  assert.match(svg, /\+\$540\.3B/);
  assert.ok(!svg.includes("Unpicked"));
  assert.ok(height > 2 * 34);
});
