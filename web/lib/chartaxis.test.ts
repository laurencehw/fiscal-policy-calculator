import assert from "node:assert/strict";
import { test } from "node:test";
import { zeroAxis } from "@/lib/chartaxis";

test("the year chart's axis always reaches zero, on round steps", () => {
  const { ticks } = zeroAxis([-25.2, -26.3, -35.6]);
  assert.equal(ticks[ticks.length - 1], 0);
  assert.ok(ticks[0] <= -35.6);
  const steps = ticks.slice(1).map((t, i) => t - ticks[i]);
  assert.ok(steps.every((s) => Math.abs(s - steps[0]) < 1e-9));
  assert.deepEqual(ticks, [-40, -30, -20, -10, 0]);
});

test("mixed and positive paths keep zero inside the axis", () => {
  const pos = zeroAxis([120, 460]).ticks;
  assert.equal(pos[0], 0);
  assert.ok(pos[pos.length - 1] >= 460);
  const mixed = zeroAxis([-30, 80]).ticks;
  assert.ok(mixed.includes(0) && mixed[0] <= -30 && mixed[mixed.length - 1] >= 80);
});
