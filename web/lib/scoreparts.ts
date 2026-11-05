// Text and numbers for the shared score-page pieces (ScoreParts.tsx), kept out
// of the component so the sign conventions and the gap sentence can be tested.
import { money, pct } from "./format";
import type { Credibility, ScoreResult } from "./types";

/**
 * One row of the year table, every column in the deficit convention
 * (positive adds to the deficit), so that
 * ``conventional + macro + debt service = dynamic`` reads straight across.
 *
 * ``dynamic_feedback`` arrives in the revenue convention (positive is more
 * revenue), which is why it is negated here: a recession that costs revenue
 * shows as a positive, deficit-increasing number beside the conventional score.
 */
export type YearRow = {
  year: number;
  revenue: number;
  conventional: number;
  macro: number;
  debtService: number | null;
  dynamic: number | null;
};

export function yearRows(c: ScoreResult, d: ScoreResult): YearRow[] {
  return c.year_by_year.map((row, i) => {
    const dyn = d.year_by_year[i];
    return {
      year: row.year,
      revenue: row.revenue_effect,
      conventional: row.final_effect,
      macro: -(dyn?.dynamic_feedback ?? 0),
      debtService: dyn?.debt_service ?? null,
      dynamic: dyn?.dynamic_effect ?? null,
    };
  });
}

/** Gap that a reader would compute from the two figures on the page. */
export function displayedGapPct(point: number, published: number): number {
  return (Math.abs(point - published) / Math.abs(published)) * 100;
}

/**
 * The "Checked against" sentence. The scorecard's error is measured on the
 * published estimate's own window and terms, which can differ from the page's
 * figure (the corporate-28% row is scored on FY2025-2034, the page on
 * FY2026-2035). When the two gaps disagree by more than half a point, say which
 * figure the error belongs to rather than attach it to "this estimate".
 */
export function checkedSentence(cred: Credibility, point: number, window: string): string {
  const published = cred.own_row_official_billions;
  if (published === null) return "No published score for this exact policy is on file.";
  const tier = cred.own_row_tier_label ? ` (${cred.own_row_tier_label.toLowerCase()})` : "";
  const err = cred.own_row_abs_pct_error;
  if (err === null) return `Published score ${money(published)}${tier}.`;
  const shown = displayedGapPct(point, published);
  if (Math.abs(shown - err) <= 0.5) {
    return `Published score ${money(published)}; this estimate is ${pct(err)} away${tier}.`;
  }
  const model = cred.own_row_model_billions;
  const run = model == null ? "The model run on the published estimate's own window and terms" : `The model run on the published estimate's own window and terms, ${money(model)},`;
  return (
    `Published score ${money(published)}${tier}. ${run} is ${pct(err)} away from it. ` +
    `The figure above is scored on ${window} against this site's baseline, so it sits ${pct(shown)} from the published number.`
  );
}
