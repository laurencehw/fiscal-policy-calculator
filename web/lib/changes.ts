// The /changes page: what moved between nightly exports, read from
// site_data/changes.json. A score change and a data refresh are kept apart, so
// a new CBO estimate in the tracker is never read as the calculator moving.
import { money } from "./format";

export type ChangeItem = {
  date: string;
  category: "score" | "data";
  kind: "preset" | "cbo_estimate" | "baseline";
  id: string;
  title: string;
  old: number | string | null;
  new: number | string | null;
  old_dynamic?: number | null;
  new_dynamic?: number | null;
  href: string;
};

export type ChangesFile = { threshold: number; items: ChangeItem[] };

export const CHANGES_DAYS = 30;

/** Items dated within `days` of `today` (YYYY-MM-DD), newest first. */
export function recentChanges(items: readonly ChangeItem[], today: string, days = CHANGES_DAYS): ChangeItem[] {
  const end = Date.parse(`${today}T00:00:00Z`);
  const start = end - days * 86_400_000;
  return items
    .filter((item) => {
      const at = Date.parse(`${item.date}T00:00:00Z`);
      return Number.isFinite(at) && at >= start && at <= end;
    })
    .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
}

/** Items grouped by date, keeping the order they come in. */
export function byDate(items: readonly ChangeItem[]): { date: string; items: ChangeItem[] }[] {
  const out: { date: string; items: ChangeItem[] }[] = [];
  for (const item of items) {
    const last = out.at(-1);
    if (last && last.date === item.date) last.items.push(item);
    else out.push({ date: item.date, items: [item] });
  }
  return out;
}

function figure(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return "none";
  return typeof value === "number" ? money(value) : value;
}

/** One sentence per item, in the page's own words. */
export function changeSentence(item: ChangeItem): string {
  if (item.kind === "preset") {
    const conv = `The conventional ten-year score moved from ${figure(item.old)} to ${figure(item.new)}`;
    const dyn =
      item.old_dynamic !== undefined && item.new_dynamic !== undefined && item.old_dynamic !== item.new_dynamic
        ? `; with macroeconomic feedback, from ${figure(item.old_dynamic)} to ${figure(item.new_dynamic)}`
        : "";
    return `${conv}${dyn}.`;
  }
  if (item.kind === "cbo_estimate") {
    return `CBO published a ten-year estimate of ${figure(item.new)}. The bill tracker now shows it.`;
  }
  return `The baseline changed from ${figure(item.old)} to ${figure(item.new)}. Every score is now on the new baseline.`;
}

export const CATEGORY_LABEL: Record<ChangeItem["category"], string> = {
  score: "Score change",
  data: "Data refresh",
};
