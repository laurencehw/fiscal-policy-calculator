// The bill tracker's list as plain data: filter by words and status, page by fifty.
import type { TrackerRow } from "./types";

export const PAGE_SIZE = 50;

export function filterBills(rows: TrackerRow[], query: string, status: string): TrackerRow[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  return rows.filter((row) => {
    if (status && row.status !== status) return false;
    if (words.length === 0) return true;
    const text = `${row.type}${row.number} ${row.type} ${row.number} ${row.title}`.toLowerCase().replace(/\./g, "");
    return words.every((word) => text.includes(word.replace(/\./g, "")));
  });
}

/** Under fifty million rounds to $0.0B; say so instead of printing a signed zero. */
export function billMoney(billions: number, money: (b: number) => string): string {
  if (billions !== 0 && Math.abs(billions) < 0.05) return billions > 0 ? "+ under $0.1B" : "- under $0.1B";
  return money(billions);
}

/**
 * Whether the calculator's automated reading of a bill may be shown as a figure: the language model
 * was at least moderately sure, no plausibility check withheld it, and it scored something.
 */
export function showsAutoFigure(row: TrackerRow): boolean {
  if (row.auto_ten_year_billions === null || row.auto_ten_year_billions === 0) return false;
  if (row.auto_withheld && row.auto_withheld.length > 0) return false;
  return row.auto_confidence === "high" || row.auto_confidence === "medium";
}
