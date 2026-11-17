// Explore's list as plain data, so the page can filter and sort it in the browser.
import type { LawStatus } from "./types";

export type ExploreRow = {
  id: string;
  name: string;
  area: string;
  conventional: number | null;
  published: number | null;
  status?: LawStatus | null;
  /** For a pre-2025-law row: its figure on the current-law baseline (see lawStatus.currentLawFigure). */
  currentLaw?: number | null;
};

export type ExploreSort = "topic" | "size";

/** Which way a row moves the deficit, for the "which policies reduce the deficit?" view. */
export type ExploreShow = "all" | "reduces" | "adds";

/** Rows the calculator scores as moving the deficit in the chosen direction. */
export function byDirection(rows: ExploreRow[], show: ExploreShow): ExploreRow[] {
  if (show === "all") return rows;
  return rows.filter((row) => row.conventional !== null && (show === "reduces" ? row.conventional < 0 : row.conventional > 0));
}

/** The starting view from the URL: ?q=, ?sort=size, ?show=reduces|adds. Unknown values fall back. */
export function viewFromQuery(search: string): { query: string; sort: ExploreSort; show: ExploreShow } {
  const params = new URLSearchParams(search);
  const sort = params.get("sort") === "size" ? "size" : "topic";
  const raw = params.get("show");
  const show: ExploreShow = raw === "reduces" || raw === "adds" ? raw : "all";
  return { query: params.get("q") ?? "", sort, show };
}

/** Rows whose name or topic contains every word of the query, case-insensitively. */
export function filterRows(rows: ExploreRow[], query: string): ExploreRow[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return rows;
  return rows.filter((row) => {
    const text = `${row.name} ${row.area}`.toLowerCase();
    return words.every((word) => text.includes(word));
  });
}

/**
 * Topic order keeps the export's grouping. Size order is one list, largest
 * effect on the deficit first in either direction; rows without a score go last.
 */
export function arrange(rows: ExploreRow[], sort: ExploreSort): { area: string | null; rows: ExploreRow[] }[] {
  if (sort === "size") {
    const sorted = [...rows].sort(
      (a, b) => Math.abs(b.conventional ?? -Infinity) - Math.abs(a.conventional ?? -Infinity),
    );
    return [{ area: null, rows: sorted }];
  }
  const groups = new Map<string, ExploreRow[]>();
  for (const row of rows) groups.set(row.area, [...(groups.get(row.area) ?? []), row]);
  return [...groups].map(([area, list]) => ({ area, rows: list }));
}

/** The largest absolute figure on the page, so every bar shares one scale. */
export function scaleOf(rows: ExploreRow[]): number {
  return Math.max(1, ...rows.flatMap((row) => [row.conventional, row.published]).map((v) => Math.abs(v ?? 0)));
}

/**
 * The line an Explore page shows beside "Add to package" when Build will list
 * the policy at a different figure. Explore leads with this calculator's
 * score; Build sums list prices, so a reader who clicks through otherwise
 * meets a second number with no warning (second external review, 2026-11-17).
 * Empty when the figures agree to the tenth of a billion or Build has no row.
 */
export function buildPriceNote(
  row: { score: number; source: string; cbo_published?: boolean } | null | undefined,
  calculator: number,
  money: (value: number) => string,
): string {
  if (!row || !Number.isFinite(row.score) || !Number.isFinite(calculator)) return "";
  if (Math.abs(row.score - calculator) < 0.05) return "";
  const who = row.cbo_published === false ? "an unpublished figure" : `${row.source}'s published score`;
  return `In a package this policy counts at ${money(row.score)}, ${who}, not the calculator's ${money(calculator)}. Build adds up published list prices.`;
}
