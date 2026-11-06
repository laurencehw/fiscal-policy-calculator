import { test } from "node:test";
import assert from "node:assert/strict";
import { evidence } from "./data";
import { CLASS_STYLE, FRAME, bandPolygon, domain, points, scaler, ticks } from "./scatter";

const rows = evidence().out_of_sample_rows;

test("one point per out-of-sample row, every class styled", () => {
  assert.equal(rows.length, evidence().out_of_sample.n);
  const pts = points(rows, domain(rows));
  assert.equal(pts.length, rows.length);
  for (const p of pts) {
    assert.ok(CLASS_STYLE[p.class], `no style for ${p.class}`);
    assert.ok(p.cx >= FRAME.left && p.cx <= FRAME.width - FRAME.right);
    assert.ok(p.cy >= FRAME.top && p.cy <= FRAME.height - FRAME.bottom);
  }
  for (const c of Object.keys(evidence().out_of_sample_classes)) assert.ok(CLASS_STYLE[c], c);
});

test("a point's error matches its distance from the 45-degree line", () => {
  for (const r of rows) {
    const err = (100 * Math.abs(r.model - r.published)) / Math.abs(r.published);
    // model and published are rounded to $0.1B, so allow that much slack on small rows
    assert.ok(Math.abs(err - r.error) < 0.15 + 10 / Math.abs(r.published), `${r.policy_id}: ${err} vs ${r.error}`);
  }
});

test("the 45-degree line maps equal values to the diagonal, and bands sit at ×(1±pct)", () => {
  const dom: [number, number] = [10, 10000];
  const s = scaler(dom);
  assert.ok(Math.abs(s.x(10) - FRAME.left) < 1e-9);
  assert.ok(Math.abs(s.y(10) - (FRAME.height - FRAME.bottom)) < 1e-9);
  assert.ok(Math.abs(s.y(10000) - FRAME.top) < 1e-9);
  const poly = bandPolygon(dom, 0.25).split(" ").map((p) => p.split(",").map(Number));
  assert.equal(poly.length, 4);
  assert.equal(poly[0][1], Number(s.y(7.5).toFixed(1)));
  assert.equal(poly[3][1], Number(s.y(12.5).toFixed(1)));
  assert.deepEqual(ticks(dom), [10, 100, 1000, 10000]);
});
