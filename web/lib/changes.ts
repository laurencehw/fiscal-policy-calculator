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

/** A new CBO estimate under $0.1B either way: listed as a count, not one line each. */
export function isNegligibleEstimate(item: ChangeItem): boolean {
  return item.kind === "cbo_estimate" && typeof item.new === "number" && Math.abs(item.new) < 0.05;
}

const REPO = "https://github.com/laurencehw/fiscal-policy-calculator/pull";

/**
 * Why a preset's score moved, for the moves a reader would otherwise have to guess at.
 * Keyed by date and preset id; the nightly export does not know why a figure moved.
 */
export const CHANGE_REASONS: Record<string, { text: string; href: string }> = {
  "2026-11-19:ss-donut-250k": {
    text: "The donut is now priced from SSA's distribution of wages against CBO's path for the taxable maximum, instead of a fitted constant",
    href: `${REPO}/262`,
  },
  "2026-11-17:corporate-28pct": {
    text: "Two changes the same day: the preset is now scored against current law, and the corporate module's credit factor was recalibrated",
    href: `${REPO}/260`,
  },
  "2026-11-17:corporate-15pct": {
    text: "Two changes the same day: the preset is now scored against current law, and the corporate module's credit factor was recalibrated",
    href: `${REPO}/260`,
  },
};
for (const id of [
  "across-the-board-rate-cut-5pp",
  "medicare-surcharge-2pp",
  "middle-class-rate-cut-2pp",
  "millionaire-surtax-5pp",
  "top-rate-39-6",
  "top-rate-45",
  "ultra-millionaire-surtax-3pp",
]) {
  CHANGE_REASONS[`2026-11-06:${id}`] = {
    text: "The IRS income base is now aged to each year on CBO's own income path",
    href: `${REPO}/246`,
  };
}

export function changeReason(item: ChangeItem): { text: string; href: string } | null {
  return CHANGE_REASONS[`${item.date}:${item.id}`] ?? null;
}
