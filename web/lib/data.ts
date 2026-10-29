// Reads the nightly export in ../site_data. Server-only: pages call these at
// build time, so the site never waits for the engine to show a preset.
import fs from "node:fs";
import path from "node:path";
import type { BuildRow, Evidence, Manifest, ScorecardEntry, PresetFile, PresetInfo, ScoreResult, TrackerIndex, TrackerRow, YearlyEffect } from "./types";

export const DATA_DIR = path.join(process.cwd(), "..", "site_data");

function read<T>(...parts: string[]): T {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, ...parts), "utf8")) as T;
}

export function manifest(): Manifest {
  return read<Manifest>("manifest.json");
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

export function buildCatalog(): BuildRow[] {
  return read<BuildRow[]>("build-catalog.json");
}

export function evidence(): Evidence {
  return read<Evidence>("validation", "evidence.json");
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
    const area = areaOf.get(info.id) ?? "Other";
    groups.set(area, [...(groups.get(area) ?? []), info]);
  }
  // The illustrative group (unfitted reconstructions) always comes last, as in the app.
  const illustrative = new Set(buildCatalog().filter((row) => row.illustrative).map((row) => row.area));
  const areas = [...new Set(buildCatalog().map((row) => row.area))];
  const order = [...areas.filter((a) => !illustrative.has(a)), "Other", ...areas.filter((a) => illustrative.has(a))];
  return order.filter((area) => groups.has(area)).map((area) => ({ area, presets: groups.get(area)! }));
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
