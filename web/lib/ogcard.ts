// What a proposal's share card shows (site review quick win 8): the figure the
// page leads with, what it measures, and the published score beside it. Kept
// out of the image route so the choices can be tested.
import { direction, money, shortLabel } from "./format";
import type { LawStatus, PresetInfo, ScoreResult } from "./types";

export type OgCard = {
  name: string;
  figure: string;
  tone: "adds" | "reduces" | "none";
  /** What the figure is, in a few words. */
  measures: string;
  /** "Reduces the deficit", or the current-law answer in words. */
  meaning: string;
  /** One line under the figure: the published score, the pre-2025 score, or nothing. */
  aside: string;
  /** The conventional path, one bar per fiscal year, deficit convention. */
  bars: number[];
};

const tone = (value: number): OgCard["tone"] => (value > 0 ? "adds" : value < 0 ? "reduces" : "none");

export function ogCard(
  c: ScoreResult,
  info: Pick<PresetInfo, "cbo_score" | "cbo_source" | "cbo_published"> & { status?: LawStatus | null },
  currentLaw: number | null,
  /** The yearly path behind ``currentLaw`` (the preset it equals); empty draws no bars. */
  currentLawBars: number[] = [],
): OgCard {
  const headline = c.ten_year_deficit_impact;
  const bars = c.year_by_year.map((row) => row.final_effect);
  const name = shortLabel(c.policy_name);
  const status = info.status;
  const answer = status?.pre_2025_law ? status.current_law : null;
  if (answer && (answer.kind === "already_law" || currentLaw !== null)) {
    const value = answer.kind === "already_law" ? 0 : (currentLaw as number);
    return {
      name,
      figure: answer.kind === "already_law" ? "$0" : money(value),
      tone: tone(value),
      measures: `Ten-year deficit effect against current law, CBO ${c.baseline_vintage} baseline`,
      meaning: answer.kind === "already_law" ? "Already law under P.L. 119-21" : direction(value),
      aside: `Against pre-2025 law: ${money(headline)}`,
      bars: answer.kind === "already_law" ? [] : currentLawBars,
    };
  }
  const published =
    info.cbo_published && info.cbo_score !== null && info.cbo_source
      ? `Published score: ${money(info.cbo_score)} (${info.cbo_source})`
      : "No published score on file";
  return {
    name,
    figure: money(headline),
    tone: tone(headline),
    measures: `Ten-year deficit effect, ${c.budget_window}${status?.pre_2025_law ? ", against pre-2025 law" : ""}`,
    meaning: direction(headline),
    aside: published,
    bars,
  };
}
