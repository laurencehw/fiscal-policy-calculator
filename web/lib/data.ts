// Reads the nightly export in ../site_data. Server-only: pages call these at
// build time, so the site never waits for the engine to show a preset.
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import type { PackageJoint } from "./packageJoint";
import type { ClassroomAssignment, ClassroomIndexRow } from "./classroom";
import type { HouseStripData } from "./houses";
import type { SSData } from "./socialSecurity";
import type { BaselineFile } from "./baseline";
import type { ChangesFile } from "./changes";
import { INDEX_NOTE, orderSnapshots, type Snapshot, type SnapshotIndex, type SnapshotIndexEntry } from "./research";
import { ARCHIVED_AREA, isArchived } from "./lawStatus";
import type { BuildRow, Evidence, Manifest, ScorecardEntry, PresetFile, PresetInfo, ResultViews, ScoreResult, StatesData, TrackerIndex, TrackerRow, ValuesArchetype, YearlyEffect } from "./types";

export const DATA_DIR = path.join(process.cwd(), "..", "site_data");

function read<T>(...parts: string[]): T {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, ...parts), "utf8")) as T;
}

/** Every frozen snapshot (scripts/site_snapshots.py), oldest first; none before the first export. */
export function snapshotIndex(): SnapshotIndex {
  const dir = path.join(DATA_DIR, "snapshots");
  const files = fs.existsSync(dir) ? fs.readdirSync(dir).filter((name) => SNAPSHOT_FILE.test(name)) : [];
  const entries: SnapshotIndexEntry[] = files.map((file) => {
    const bytes = fs.readFileSync(path.join(dir, file));
    const data = JSON.parse(bytes.toString("utf8")) as Snapshot;
    return {
      id: data.id,
      scores_date: data.scores_date,
      scores_fingerprint: data.scores_fingerprint,
      file,
      sha256: createHash("sha256").update(bytes).digest("hex"),
      bytes: bytes.length,
      presets: data.presets.length,
      build_rows: data.build_catalog.length,
      previous_snapshot_id: data.previous_snapshot_id ?? null,
      previous_sha256: data.previous_sha256 ?? null,
      source_commit: data.source_commit ?? null,
    };
  });
  return { note: INDEX_NOTE, snapshots: orderSnapshots(entries) };
}

const SNAPSHOT_FILE = /^\d{4}-\d{2}-\d{2}-[0-9a-f]{12}\.json$/;

/** One snapshot's file, as text (served byte for byte) and parsed. */
export function snapshotFile(entry: SnapshotIndexEntry): { text: string; data: Snapshot } {
  if (!SNAPSHOT_FILE.test(entry.file)) throw new Error(`bad snapshot file name ${entry.file}`);
  const text = fs.readFileSync(path.join(DATA_DIR, "snapshots", entry.file), "utf8");
  return { text, data: JSON.parse(text) as Snapshot };
}

export function manifest(): Manifest {
  return read<Manifest>("manifest.json");
}

/** What moved between nightly exports. Empty when the file is missing (an export from before U8). */
export function changes(): ChangesFile {
  const file = path.join(DATA_DIR, "changes.json");
  if (!fs.existsSync(file)) return { threshold: 0.005, items: [] };
  return read<ChangesFile>("changes.json");
}

export function presets(): PresetInfo[] {
  return read<{ presets: PresetInfo[] }>("presets", "index.json").presets;
}

export function preset(id: string): PresetFile | null {
  if (!/^[a-z0-9-]+$/.test(id)) return null;
  const file = path.join(DATA_DIR, "presets", `${id}.json`);
  if (!fs.existsSync(file)) return null;
  return read<PresetFile>("presets", `${id}.json`);
}

export function views(id: string): ResultViews | null {
  if (!/^[a-z0-9-]+$/.test(id)) return null;
  const file = path.join(DATA_DIR, "views", `${id}.json`);
  if (!fs.existsSync(file)) return null;
  return read<ResultViews>("views", `${id}.json`);
}

export function classroomIndex(): ClassroomIndexRow[] {
  return read<ClassroomIndexRow[]>("classroom", "index.json");
}

export function classroomAssignment(id: string): ClassroomAssignment | null {
  if (!/^[a-z0-9_]+$/.test(id)) return null;
  const file = path.join(DATA_DIR, "classroom", `${id}.json`);
  if (!fs.existsSync(file)) return null;
  return read<ClassroomAssignment>("classroom", `${id}.json`);
}

export function statesData(): StatesData {
  return read<StatesData>("states.json");
}

/** The Build catalog, with presets scored against pre-2025 law moved into the archived group. */
export function buildCatalog(): BuildRow[] {
  return read<BuildRow[]>("build-catalog.json").map((row) =>
    isArchived(row.status) ? { ...row, area: ARCHIVED_AREA } : row,
  );
}

/** Build's interaction channels and the microsim's measured overlaps (bet 4). */
export function packageJoint(): PackageJoint {
  return read<PackageJoint>("package-joint.json");
}

export function evidence(): Evidence {
  return read<Evidence>("validation", "evidence.json");
}

export function houseStrip(id: string): HouseStripData | null {
  if (!/^[a-z0-9-]+$/.test(id)) return null;
  const all = read<Record<string, HouseStripData>>("ranges.json");
  return all[id] ?? null;
}

export function baseline(): BaselineFile {
  return read<BaselineFile>("baseline.json");
}

export function scorecardEntries(): ScorecardEntry[] {
  return read<{ entries: ScorecardEntry[] }>("validation", "scorecard.json").entries;
}

export type Tier = "out_of_sample" | "fitted" | "reconstruction" | "retired";

/**
 * The tier each benchmark reports in, as the validation scripts split them:
 * out-of-sample predictions, fitted references, unfitted reconstructions, and
 * targets withdrawn for want of a document. Never pooled.
 */
export function tierOf(entry: ScorecardEntry): Tier {
  if (entry.holdout_status === "generic_reference") return "out_of_sample";
  if (entry.target_retired) return "retired";
  return entry.calibrated_to_target ? "fitted" : "reconstruction";
}

export function scoreSchema(): { properties: Record<string, unknown>; $defs: Record<string, { properties: Record<string, unknown> }> } {
  return read("schema", `score-result.v${manifest().schema_version}.json`);
}

/** Presets grouped by the Build catalog's area, in catalog order; the rest under "Other". */
export function presetsByArea(): { area: string; presets: PresetInfo[] }[] {
  const areaOf = new Map(buildCatalog().map((row) => [row.build_id, row.area]));
  const groups = new Map<string, PresetInfo[]>();
  for (const info of presets()) {
    const area = isArchived(info.status) ? ARCHIVED_AREA : (areaOf.get(info.id) ?? "Other");
    groups.set(area, [...(groups.get(area) ?? []), info]);
  }
  // The illustrative group (unfitted reconstructions) comes after the live areas, as in
  // the app, and the archived pre-2025-law group comes last of all.
  const catalog = buildCatalog();
  const illustrative = new Set(catalog.filter((row) => row.illustrative).map((row) => row.area));
  const areas = [...new Set(catalog.map((row) => row.area))].filter((a) => a !== ARCHIVED_AREA);
  const order = [
    ...areas.filter((a) => !illustrative.has(a)),
    "Other",
    ...areas.filter((a) => illustrative.has(a)),
    ARCHIVED_AREA,
  ];
  return order.filter((area) => groups.has(area)).map((area) => ({ area, presets: groups.get(area)! }));
}

export function valuesArchetypes(): ValuesArchetype[] {
  return read<{ archetypes: ValuesArchetype[] }>("values.json").archetypes;
}

export function socialSecurity(): SSData {
  return read<SSData>("social-security.json");
}

export function trackerIndex(): TrackerIndex {
  return read<TrackerIndex>("tracker", "index.json");
}

/**
 * The tracker's bills with a fiscal estimate (decision F4, option b), largest first.
 * CBO's own estimates; then the calculator's reading of the bill text, which is
 * demo-grade, so low-confidence readings are kept apart from the rest.
 */
export function trackerGroups(index: TrackerIndex = trackerIndex()): {
  cbo: TrackerRow[];
  auto: TrackerRow[];
  autoLow: TrackerRow[];
} {
  const size = (v: number | null) => Math.abs(v ?? 0);
  const bySize = (key: "cbo_ten_year_billions" | "auto_ten_year_billions") => (a: TrackerRow, b: TrackerRow) =>
    size(b[key]) - size(a[key]) || a.id.localeCompare(b.id);
  const cbo = index.rows.filter((r) => r.cbo_ten_year_billions !== null).sort(bySize("cbo_ten_year_billions"));
  const autoOnly = index.rows.filter((r) => r.cbo_ten_year_billions === null && r.auto_ten_year_billions !== null);
  const confident = (r: TrackerRow) => r.auto_confidence === "high" || r.auto_confidence === "medium";
  return {
    cbo,
    auto: autoOnly.filter(confident).sort(bySize("auto_ten_year_billions")),
    autoLow: autoOnly.filter((r) => !confident(r)).sort(bySize("auto_ten_year_billions")),
  };
}

const CSV_COLUMNS: (keyof YearlyEffect)[] = [
  "year",
  "revenue_effect",
  "behavioral_offset",
  "final_effect",
  "dynamic_feedback",
  "debt_service",
  "dynamic_effect",
];

/** One row per fiscal year: the conventional path, then the dynamic view's columns. */
export function yearCsv(conventional: ScoreResult, dynamic: ScoreResult): string {
  const lines = [
    `# ${conventional.policy_name.replace(/\\\$/g, "$")}`,
    `# Baseline ${conventional.baseline_vintage}, ${conventional.budget_window}. Billions of dollars.`,
    "# final_effect and dynamic_effect: positive increases the deficit. revenue_effect and dynamic_feedback: positive is more revenue.",
    CSV_COLUMNS.join(","),
  ];
  conventional.year_by_year.forEach((row, i) => {
    const dyn = dynamic.year_by_year[i];
    const merged: YearlyEffect = { ...row, dynamic_feedback: dyn?.dynamic_feedback ?? 0, debt_service: dyn?.debt_service ?? null, dynamic_effect: dyn?.dynamic_effect ?? null };
    lines.push(CSV_COLUMNS.map((col) => (merged[col] === null ? "" : String(merged[col]))).join(","));
  });
  return lines.join("\n") + "\n";
}
