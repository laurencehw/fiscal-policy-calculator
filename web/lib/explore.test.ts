import { test } from "node:test";
import assert from "node:assert/strict";
import { arrange, buildPriceNote, byDirection, filterRows, scaleOf, viewFromQuery, type ExploreRow } from "./explore";

const rows: ExploreRow[] = [
  { id: "a", name: "TCJA Full Extension", area: "TCJA / Individual", conventional: 4581.9, published: 4600 },
  { id: "b", name: "Biden Corporate 28%", area: "Corporate", conventional: -1310.9, published: -1347 },
  { id: "c", name: "Repeal EV Credits", area: "Climate / energy", conventional: -228.4, published: null },
  { id: "d", name: "Trump Corporate 15%", area: "Corporate", conventional: 1562.8, published: 673 },
];

test("filtering matches every word against the name and the topic", () => {
  assert.deepEqual(filterRows(rows, "corporate").map((r) => r.id), ["b", "d"]);
  assert.deepEqual(filterRows(rows, "  corporate  trump ").map((r) => r.id), ["d"]);
  assert.deepEqual(filterRows(rows, "climate").map((r) => r.id), ["c"]);
  assert.equal(filterRows(rows, "").length, 4);
});

test("topic order keeps the export's groups; size order is one list by absolute effect", () => {
  assert.deepEqual(arrange(rows, "topic").map((g) => g.area), ["TCJA / Individual", "Corporate", "Climate / energy"]);
  const size = arrange(rows, "size");
  assert.equal(size.length, 1);
  assert.deepEqual(size[0].rows.map((r) => r.id), ["a", "d", "b", "c"]);
});

test("bars share one scale, the largest figure of either kind", () => {
  assert.equal(scaleOf(rows), 4600);
  assert.equal(scaleOf([]), 1);
});

test("the direction filter and the URL view", () => {
  assert.deepEqual(byDirection(rows, "reduces").map((r) => r.id), ["b", "c"]);
  assert.deepEqual(byDirection(rows, "adds").map((r) => r.id), ["a", "d"]);
  assert.equal(byDirection(rows, "all").length, 4);
  assert.deepEqual(viewFromQuery("?show=reduces&sort=size"), { query: "", sort: "size", show: "reduces" });
  assert.deepEqual(viewFromQuery("?show=bogus&sort=x&q=tariff"), { query: "tariff", sort: "topic", show: "all" });
});

test("Explore warns when Build will list the policy at another figure (second review)", () => {
  const money = (v: number) => `${v < 0 ? "-" : "+"}$${Math.abs(v).toFixed(1)}B`;
  const note = buildPriceNote({ score: -245.9, source: "Treasury", cbo_published: true }, -309.76, money);
  assert.match(note, /-\$245\.9B, Treasury's published score, not the calculator's -\$309\.8B/);
  assert.equal(buildPriceNote({ score: -309.8, source: "Treasury" }, -309.76, money), "");
  assert.equal(buildPriceNote(null, -309.76, money), "");
  assert.match(buildPriceNote({ score: -100, source: "x", cbo_published: false }, -50, money), /an unpublished figure/);
});
