// The research layer: frozen snapshots of the scored figures (written by
// scripts/site_snapshots.py into site_data/snapshots/) and the read-only JSON
// API under /api/v1 that serves them. Everything the API returns comes from a
// snapshot file, so "the current figures" are simply the newest snapshot and a
// researcher who saved an old link can always get the same numbers back.

export const API_VERSION = "v1";
export const API_BASE = `/api/${API_VERSION}`;

export type SnapshotIndexEntry = {
  id: string;
  scores_date: string;
  scores_fingerprint: string;
  file: string;
  sha256: string;
  bytes: number;
  presets: number;
  build_rows: number;
  previous_snapshot_id: string | null;
  previous_sha256: string | null;
  source_commit: string | null;
};

export type SnapshotIndex = { note: string; snapshots: SnapshotIndexEntry[] };

export const INDEX_NOTE =
  "One frozen snapshot per scores fingerprint, oldest first. A snapshot is never rewritten, and each records the sha256 of the one before it. Where one scores date has several snapshots, the last is what the site showed at the end of that day.";

/**
 * Oldest first: by scores date, then by each snapshot's previous_snapshot_id
 * chain within a day, then by id. scripts/site_snapshots.py orders the same way.
 */
export function orderSnapshots(entries: SnapshotIndexEntry[]): SnapshotIndexEntry[] {
  const byId = new Map(entries.map((entry) => [entry.id, entry]));
  const depth = (entry: SnapshotIndexEntry): number => {
    const seen = new Set<string>();
    let count = 0;
    let current = entry;
    for (;;) {
      const parent = byId.get(current.previous_snapshot_id ?? "");
      if (!parent || parent.scores_date !== entry.scores_date || seen.has(parent.id)) return count;
      seen.add(parent.id);
      count += 1;
      current = parent;
    }
  };
  return [...entries].sort(
    (a, b) => a.scores_date.localeCompare(b.scores_date) || depth(a) - depth(b) || a.id.localeCompare(b.id),
  );
}

type Num = number | null;

export type SnapshotPreset = {
  id: string;
  name: string;
  law_status: string | null;
  published: { billions: Num; source: string | null; date: string | null; is_published_score: boolean | null };
  conventional: {
    budget_window: string | null;
    baseline_vintage: string | null;
    ten_year_deficit_impact?: Num;
    static_revenue_effect?: Num;
    behavioral_offset?: Num;
    final_static_effect?: Num;
    year_by_year: Record<string, Num>[];
  };
  dynamic: {
    model: string | null;
    dynamic_adjusted_impact?: Num;
    ten_year_deficit_impact?: Num;
    revenue_feedback?: Num;
    debt_service?: Num;
    gdp_effect?: Num;
    employment_effect?: Num;
    year_by_year: Record<string, Num>[];
  };
  error_band: Record<string, unknown>;
};

export type Snapshot = {
  schema: string;
  id: string;
  scores_date: string;
  scores_fingerprint: string;
  export_schema_version: number | null;
  baseline_vintages: string[];
  budget_windows: string[];
  sign_convention: string | null;
  units: string;
  fingerprint_covers: string;
  repository: string;
  license: string;
  source_commit?: string;
  previous_snapshot_id?: string;
  previous_sha256?: string | null;
  presets: SnapshotPreset[];
  build_catalog: Record<string, unknown>[];
  validation: Record<string, unknown> | null;
};

const DATE = /^\d{4}-\d{2}-\d{2}$/;
const ID = /^\d{4}-\d{2}-\d{2}-[0-9a-f]{12}$/;

/** The newest snapshot in the index, or null when there are none. */
export function latestEntry(index: SnapshotIndex): SnapshotIndexEntry | null {
  return index.snapshots.length ? index.snapshots[index.snapshots.length - 1] : null;
}

/**
 * Which snapshot a reference names: "latest", a full id ("2026-11-19-c504675255ed"),
 * or a scores date, which resolves to that day's last snapshot, the figures the
 * site showed at the end of it. A `v=` stamp on a share link is such a date.
 */
export function resolveSnapshot(index: SnapshotIndex, ref: string): SnapshotIndexEntry | null {
  const text = ref.trim();
  if (text === "latest") return latestEntry(index);
  if (ID.test(text)) return index.snapshots.find((entry) => entry.id === text) ?? null;
  if (DATE.test(text)) {
    const sameDay = index.snapshots.filter((entry) => entry.scores_date === text);
    return sameDay.length ? sameDay[sameDay.length - 1] : null;
  }
  return null;
}

/** Every reference the API answers for: each id, each date that has a snapshot, and "latest". */
export function snapshotRefs(index: SnapshotIndex): string[] {
  const dates = [...new Set(index.snapshots.map((entry) => entry.scores_date))];
  return [...index.snapshots.map((entry) => entry.id), ...dates, ...(index.snapshots.length ? ["latest"] : [])];
}

/** One line per preset for /api/v1/presets: the headline figures and where the full record is. */
/** A preset's name without the emoji the app's labels open with ("🏛️ TCJA Full Extension"). */
export function plainName(name: string): string {
  return name.replace(/^[^\p{L}\p{N}(]+/u, "").trim() || name;
}

export function presetSummaries(snapshot: Snapshot, site: string) {
  return snapshot.presets.map((item) => ({
    id: item.id,
    name: plainName(item.name),
    law_status: item.law_status,
    budget_window: item.conventional.budget_window,
    baseline_vintage: item.conventional.baseline_vintage,
    conventional_billions: item.conventional.ten_year_deficit_impact ?? null,
    dynamic_billions: item.dynamic.dynamic_adjusted_impact ?? null,
    // Only a score someone published. The repository's own estimates sit in the preset
    // file for reference, but a field named published_billions must not carry one.
    published_billions: item.published.is_published_score === false ? null : item.published.billions,
    published_source: item.published.is_published_score === false ? null : item.published.source,
    api_url: `${site}${API_BASE}/presets/${item.id}`,
    page_url: `${site}/explore/${item.id}?v=${snapshot.id}`,
  }));
}

/** The fields every API response opens with, so a saved file says where and when it came from. */
export function provenance(snapshot: Snapshot, site: string) {
  return {
    api_version: API_VERSION,
    snapshot_id: snapshot.id,
    scores_date: snapshot.scores_date,
    source_commit: snapshot.source_commit ?? null,
    scores_fingerprint: snapshot.scores_fingerprint,
    snapshot_url: `${site}${API_BASE}/snapshots/${snapshot.id}`,
    documentation: `${site}/data`,
    sign_convention: snapshot.sign_convention,
    units: snapshot.units,
    license: snapshot.license,
  };
}

/** The API's front door: what each endpoint returns. */
export function apiDirectory(index: SnapshotIndex, site: string) {
  const latest = latestEntry(index);
  const base = `${site}${API_BASE}`;
  return {
    name: "Fiscal Policy Calculator data API",
    api_version: API_VERSION,
    documentation: `${site}/data`,
    read_only: true,
    authentication: "none",
    latest_snapshot: latest ? { id: latest.id, scores_date: latest.scores_date, url: `${base}/snapshots/${latest.id}` } : null,
    snapshots: index.snapshots.length,
    endpoints: [
      { path: `${API_BASE}`, returns: "This list." },
      { path: `${API_BASE}/presets`, returns: "Every Explore preset with its ten-year figures, from the latest snapshot." },
      { path: `${API_BASE}/presets/{id}`, returns: "One preset in full: components, year-by-year paths, published score and error band." },
      { path: `${API_BASE}/build`, returns: "Build's list prices, from the latest snapshot." },
      { path: `${API_BASE}/validation`, returns: "The validation tiers the Methods page quotes, from the latest snapshot." },
      { path: `${API_BASE}/snapshots`, returns: "Every frozen snapshot, oldest first, with its sha256." },
      { path: `${API_BASE}/snapshots/{ref}`, returns: "One snapshot in full. ref is a snapshot id, a scores date (that day's last snapshot) or latest." },
    ],
    sign_convention: "Billions of dollars over the budget window; positive increases the deficit, negative reduces it.",
  };
}
