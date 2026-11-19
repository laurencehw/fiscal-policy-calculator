// The one plain-language sentence that opens an Explore page (site review quick
// win 6). Every number in it is already on the page: the ten-year headline,
// the "Who pays" table and the "Checked against" box. Nothing here is scored.
import { money } from "./format";
import type { Credibility, DistGrouping, LawStatus, ScoreResult } from "./types";

/** "$104B", "$9.5B", "$1.2T": a rounded size with no sign, for prose. */
export function roughMoney(billions: number): string {
  const abs = Math.abs(billions);
  if (abs >= 1000) return `$${(abs / 1000).toFixed(1)}T`;
  if (abs >= 10) return `$${Math.round(abs).toLocaleString("en-US")}B`;
  return `$${abs.toFixed(1)}B`;
}

/** "$1M", "$500K", "$100K": an income floor as people say it. */
export function incomeFloor(dollars: number): string {
  if (dollars >= 1_000_000) return `$${+(dollars / 1_000_000).toFixed(1)}M`;
  return `$${Math.round(dollars / 1000)}K`;
}

/** "Cuts the deficit by about $104B a year": the headline as a yearly average. */
export function sizeClause(c: Pick<ScoreResult, "ten_year_deficit_impact" | "year_by_year">): string {
  const total = c.ten_year_deficit_impact;
  const years = c.year_by_year.length || 10;
  if (!Number.isFinite(total) || Math.abs(total) < 0.05) return "Leaves the deficit about where it is";
  const each = roughMoney(total / years);
  return total < 0 ? `Cuts the deficit by about ${each} a year` : `Adds about ${each} a year to the deficit`;
}

/**
 * Who carries the tax change, from the income-band table: the fewest top bands
 * that hold at least three quarters of it. Empty when the table is missing, when
 * bands pull in opposite directions, or when the change is spread from low
 * incomes up, since a floor near zero says nothing.
 */
export function whoClause(table: DistGrouping | undefined): string {
  if (!table || !table.groups.length) return "";
  if (!Number.isFinite(table.total_tax_change_billions) || Math.abs(table.total_tax_change_billions) < 0.5) return "";
  if (table.groups.some((g) => g.share_of_total < -0.02)) return "";
  const top = [...table.groups].sort((a, b) => b.floor - a.floor);
  let share = 0;
  let floor = 0;
  for (const group of top) {
    share += group.share_of_total;
    floor = group.floor;
    if (share >= 0.75) break;
  }
  if (share < 0.75 || floor < 100_000) return "";
  const raises = table.total_tax_change_billions > 0;
  const amount = share >= 0.95 ? "nearly all of it" : share >= 0.85 ? `about ${Math.round(share * 100)}% of it` : `${Math.round(share * 100)}% of it`;
  return raises
    ? `${amount} paid by people with incomes over ${incomeFloor(floor)}`
    : `${amount} going to people with incomes over ${incomeFloor(floor)}`;
}

/** How well this calculator does on policies like this one, in words. */
export function checkClause(cred: Credibility | null, isPublished = true): string {
  if (!cred) return "There is no published score to check it against.";
  const err = cred.own_row_abs_pct_error;
  const published = cred.own_row_official_billions;
  if (!isPublished && published !== null) {
    return `No published score checks it: the reference figure on file, ${money(published)}, is not a published estimate.`;
  }
  if (cred.own_row_tier === "fitted" && published !== null) {
    return `The calculator is calibrated to a published score of ${money(published)}, so the two agree by design.`;
  }
  if (err !== null && published !== null && cred.own_row_tier) {
    const off = Math.round(err);
    if (off < 1) return `This calculator's figure is within 1% of the published score of ${money(published)}.`;
    const tail = off > 50 ? ", a large miss, so read it as illustrative" : "";
    return `This calculator's figure is about ${off}% off the published score of ${money(published)}${tail}.`;
  }
  if (cred.mean_abs_pct_error !== null && cred.n_tier1_rows > 0 && cred.class_label) {
    return (
      `On policies like this (${pluralClass(cred.class_label)}), this calculator has missed published scores ` +
      `by about ${Math.round(cred.mean_abs_pct_error)}% on average.`
    );
  }
  return "There is no published score to check it against.";
}

/** The out-of-sample class label as a plural a reader would use. */
const CLASS_WORDS: Record<string, string> = {
  "ordinary rate change": "income tax rate changes",
  "AGI-inclusive surtax": "income surtaxes",
  "capital gains": "capital gains changes",
  corporate: "corporate rate changes",
  payroll: "payroll tax changes",
  "tax expenditure": "changes to deductions and exclusions",
  "enacted-law spending": "spending laws",
  "discretionary spending": "discretionary spending changes",
};

export function pluralClass(label: string): string {
  return CLASS_WORDS[label] ?? label;
}

/**
 * For a preset built on pre-2025 law, the takeaway leads with today's answer,
 * which the box below the title shows in full.
 */
export function currentLawClause(status: LawStatus | null | undefined, figure: number | null): string {
  const answer = status?.current_law;
  if (!status?.pre_2025_law || !answer) return "";
  if (answer.kind === "already_law") return "This is already law under P.L. 119-21, so against today's baseline it changes nothing.";
  if (figure === null) return "Part of this is already law under P.L. 119-21, and the rest is not scored against today's baseline.";
  return `Against today's baseline, which includes P.L. 119-21, it ${figure < 0 ? "cuts the deficit by" : "adds"} about ${roughMoney(figure)} over ten years${figure < 0 ? "" : " to the deficit"}.`;
}

/** The sentence an Explore page opens with. */
export function takeaway({
  c,
  table,
  status,
  currentLaw,
  isPublished = true,
}: {
  c: ScoreResult;
  /** False when the preset's reference figure is this repository's own or a withdrawn target (index cbo_published). */
  isPublished?: boolean;
  table?: DistGrouping;
  status?: LawStatus | null;
  currentLaw?: number | null;
}): string {
  const law = currentLawClause(status, currentLaw ?? null);
  if (law) return `${law} The figures below answer the pre-2025 question.`;
  const who = whoClause(table);
  const first = who ? `${sizeClause(c)}, ${who}.` : `${sizeClause(c)}.`;
  return `${first} ${checkClause(c.credibility, isPublished)}`;
}
