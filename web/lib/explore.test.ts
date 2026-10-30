import { test } from "node:test";
import assert from "node:assert/strict";
import { arrange, filterRows, scaleOf, type ExploreRow } from "./explore";

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
