// Explore's list as plain data, so the page can filter and sort it in the browser.

export type ExploreRow = {
  id: string;
  name: string;
  area: string;
  conventional: number | null;
  published: number | null;
};

export type ExploreSort = "topic" | "size";

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
