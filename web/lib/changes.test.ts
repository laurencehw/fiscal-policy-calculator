import { test } from "node:test";
import assert from "node:assert/strict";
import { byDate, changeSentence, recentChanges, type ChangeItem } from "./changes";
import { changes } from "./data";

function item(date: string, id: string, extra: Partial<ChangeItem> = {}): ChangeItem {
  return { date, category: "score", kind: "preset", id, title: id, old: -100, new: -102, href: `/explore/${id}`, ...extra };
}

test("the page lists the last 30 days, newest first", () => {
  const list = recentChanges([item("2026-09-01", "old"), item("2026-11-01", "b"), item("2026-11-05", "a")], "2026-11-06");
  assert.deepEqual(list.map((i) => i.id), ["a", "b"]);
  assert.deepEqual(byDate([item("2026-11-05", "a"), item("2026-11-05", "c"), item("2026-11-01", "b")]).map((g) => g.items.length), [2, 1]);
});

test("each kind gets its own sentence, and a score change is never called a refresh", () => {
  assert.match(changeSentence(item("2026-11-05", "a", { old_dynamic: -90, new_dynamic: -95 })), /from -\$100\.0B to -\$102\.0B; with macroeconomic feedback, from -\$90\.0B to -\$95\.0B/);
  assert.match(changeSentence(item("2026-11-05", "s", { category: "data", kind: "cbo_estimate", old: null, new: -40 })), /CBO published a ten-year estimate of -\$40\.0B/);
  assert.match(changeSentence(item("2026-11-05", "baseline", { category: "data", kind: "baseline", old: "January 2025", new: "February 2026" })), /January 2025 to February 2026/);
});

test("the exported changes file reads", () => {
  const file = changes();
  assert.ok(Array.isArray(file.items));
});
