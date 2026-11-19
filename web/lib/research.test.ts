import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { snapshotFile, snapshotIndex } from "./data";
import {
  apiDirectory,
  latestEntry,
  orderSnapshots,
  presetSummaries,
  provenance,
  resolveSnapshot,
  snapshotRefs,
  type SnapshotIndex,
  type SnapshotIndexEntry,
} from "./research";

const entry = (id: string, extra: Partial<SnapshotIndexEntry> = {}): SnapshotIndexEntry => ({
  id,
  scores_date: id.slice(0, 10),
  scores_fingerprint: id.slice(11),
  file: `${id}.json`,
  sha256: "0".repeat(64),
  bytes: 1,
  presets: 1,
  build_rows: 1,
  previous_snapshot_id: null,
  previous_sha256: null,
  source_commit: null,
  ...extra,
});

const INDEX: SnapshotIndex = {
  note: "",
  snapshots: [entry("2026-11-05-aaaaaaaaaaaa"), entry("2026-11-17-bbbbbbbbbbbb"), entry("2026-11-17-cccccccccccc")],
};

test("a reference resolves by id, by date (that day's last), or latest", () => {
  assert.equal(resolveSnapshot(INDEX, "2026-11-17-bbbbbbbbbbbb")?.id, "2026-11-17-bbbbbbbbbbbb");
  assert.equal(resolveSnapshot(INDEX, "2026-11-17")?.id, "2026-11-17-cccccccccccc");
  assert.equal(resolveSnapshot(INDEX, "2026-11-05")?.id, "2026-11-05-aaaaaaaaaaaa");
  assert.equal(resolveSnapshot(INDEX, "latest")?.id, "2026-11-17-cccccccccccc");
  // A date with no snapshot, or anything else, is not guessed at.
  assert.equal(resolveSnapshot(INDEX, "2026-11-06"), null);
  assert.equal(resolveSnapshot(INDEX, "../manifest"), null);
  assert.equal(resolveSnapshot({ ...INDEX, snapshots: [] }, "latest"), null);
  assert.deepEqual(snapshotRefs(INDEX), [
    "2026-11-05-aaaaaaaaaaaa",
    "2026-11-17-bbbbbbbbbbbb",
    "2026-11-17-cccccccccccc",
    "2026-11-05",
    "2026-11-17",
    "latest",
  ]);
  assert.deepEqual(snapshotRefs({ ...INDEX, snapshots: [] }), []);
});

test("the directory lists every route the API serves", () => {
  const dir = apiDirectory(INDEX, "https://x.org");
  assert.equal(dir.latest_snapshot?.url, "https://x.org/api/v1/snapshots/2026-11-17-cccccccccccc");
  const routes = fs
    .readdirSync(path.join(process.cwd(), "app", "api", "v1"), { recursive: true })
    .map(String)
    .filter((file) => file.endsWith("route.ts"))
    .map((file) => `/api/v1/${path.dirname(file)}`.replace(/\/\.$/, "").replace(/\[(\w+)\]/g, "{$1}").replace(/\\/g, "/"))
    .sort();
  assert.deepEqual(dir.endpoints.map((row) => row.path).sort(), routes);
});

test("within a day, snapshots follow their previous_snapshot_id chain, not their ids", () => {
  const a = entry("2026-11-17-ffffffffffff", { previous_snapshot_id: "2026-11-06-aaaaaaaaaaaa" });
  const b = entry("2026-11-17-111111111111", { previous_snapshot_id: a.id });
  const c = entry("2026-11-19-000000000000", { previous_snapshot_id: b.id });
  const first = entry("2026-11-06-aaaaaaaaaaaa");
  assert.deepEqual(orderSnapshots([c, b, first, a]).map((row) => row.id), [first.id, a.id, b.id, c.id]);
  // A loop in the chain cannot hang the sort.
  const x = entry("2026-11-20-aaaaaaaaaaaa", { previous_snapshot_id: "2026-11-20-bbbbbbbbbbbb" });
  const y = entry("2026-11-20-bbbbbbbbbbbb", { previous_snapshot_id: x.id });
  assert.equal(orderSnapshots([x, y]).length, 2);
});

test("the committed snapshots form an unbroken hash chain, and the newest is the current export", () => {
  const index = snapshotIndex();
  assert.ok(index.snapshots.length > 0);
  const byId = new Map(index.snapshots.map((row) => [row.id, row]));
  index.snapshots.forEach((row, i) => {
    assert.equal(row.file, `${row.id}.json`);
    assert.equal(row.id, `${row.scores_date}-${row.scores_fingerprint}`);
    if (i > 0) {
      // Each snapshot names the one before it and that file's sha256; an edit to an old one breaks this.
      assert.equal(row.previous_snapshot_id, index.snapshots[i - 1].id, row.id);
      assert.equal(row.previous_sha256, byId.get(row.previous_snapshot_id!)!.sha256, row.id);
    }
  });
  const manifest = JSON.parse(fs.readFileSync(path.join(process.cwd(), "..", "site_data", "manifest.json"), "utf8"));
  const latest = latestEntry(index)!;
  assert.equal(latest.scores_fingerprint, manifest.scores_fingerprint);
  assert.equal(latest.scores_date, manifest.scores_date);

  const { data: snapshot } = snapshotFile(latest);
  const head = provenance(snapshot, "https://x.org");
  assert.equal(head.snapshot_id, latest.id);
  assert.match(head.sign_convention ?? "", /positive increases the deficit/);
  const rows = presetSummaries(snapshot, "https://x.org");
  assert.equal(rows.length, manifest.presets);
  for (const row of rows) {
    // The summary is the preset's own figure, to within the fingerprint's rounding.
    const file = JSON.parse(fs.readFileSync(path.join(process.cwd(), "..", "site_data", "presets", `${row.id}.json`), "utf8"));
    assert.ok(Math.abs((row.conventional_billions ?? NaN) - file.conventional.ten_year_deficit_impact) < 0.06, row.id);
    assert.equal(row.page_url, `https://x.org/explore/${row.id}?v=${manifest.scores_date}`);
  }
});
