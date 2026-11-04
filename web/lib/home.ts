import { evidence, manifest, presets, scorecardEntries, tierOf, trackerIndex, type Tier } from "./data";
import { money } from "./format";

/**
 * Three out-of-sample scorecard rows, not fitted reproductions.
 * One within 5% of its published score, one beside the ordinary-rate class
 * mean, and one corporate miss. Dollars are read from the nightly scorecard.
 * None of the three has a preset page, so each links to its row on Methods.
 */
export const WORKED_POLICY_IDS = [
  "cbo_opt45_all_rates_1pp",
  "cbo2021_opt1_all_rates_1pp",
  "cbo_opt64_corporate_rate_1pp",
] as const;

export type WorkedRow = {
  id: string;
  name: string;
  href: string;
  conventional: number;
  published: number;
  source: string;
  tier: Tier;
  gapPct: number;
};

export function tierPhrase(tier: Tier, gapPct: number): string {
  const gap = `${gapPct.toFixed(1)}% from the published score`;
  if (tier === "fitted") return `Fitted to the published score.`;
  if (tier === "out_of_sample") return `Out-of-sample prediction, ${gap}.`;
  if (tier === "reconstruction") return `Unfitted reconstruction, ${gap}.`;
  return "Withdrawn target, kept on the record.";
}

export function workedRows(): WorkedRow[] {
  const byPolicy = new Map(scorecardEntries().map((entry) => [entry.policy_id, entry]));
  return WORKED_POLICY_IDS.map((id) => {
    const entry = byPolicy.get(id);
    if (!entry) throw new Error(`worked policy ${id} is not in the scorecard`);
    const tier = tierOf(entry);
    const published = entry.official_10yr_billions;
    const gapPct = published === 0 ? 0 : (Math.abs(entry.model_10yr_billions - published) / Math.abs(published)) * 100;
    return {
      id,
      name: entry.policy_name,
      href: `/methods#bench-${id}`,
      conventional: entry.model_10yr_billions,
      published,
      source: entry.official_source,
      tier,
      gapPct,
    };
  });
}

/** Prose under the title. The two figures on a row are different quantities. */
export function homeSectionParagraphs(): string[] {
  const m = manifest();
  return [
    m.sign_convention,
    `The baseline is CBO's ${m.baseline_vintages.join(" and ")} vintage, and the window is ${m.budget_windows.join(", ")}.`,
    "On each line below, the first figure is this calculator's conventional ten-year estimate and the second is the published score I check the same policy against. These are different quantities: Explore lists the calculator's score, while Build lists the published list price. I do not retune the calculator to make the two match, so where they differ the gap tells us something about the model. The three lines are out-of-sample predictions: I did not fit the model to them. A fitted row, when I show one, says so.",
  ];
}

export function homeRowLine(row: WorkedRow): string {
  return `${row.name}: calculator ${money(row.conventional)}; published ${money(row.published)} (${row.source}). ${tierPhrase(row.tier, row.gapPct)}`;
}

export function homeSectionText(): string {
  const rows = workedRows().map(homeRowLine);
  return ["How to read a figure", ...homeSectionParagraphs(), ...rows].join(" ");
}

export type HomeStat = { figure: string; label: string; href: string };

/** The strip under the title. Every figure is read from the nightly export. */
export function homeStats(): HomeStat[] {
  const m = manifest();
  const oos = evidence().out_of_sample;
  const tracker = trackerIndex();
  const updated = tracker.last_update
    ? new Date(tracker.last_update).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" })
    : null;
  return [
    { figure: String(presets().length), label: "proposals scored on CBO's baseline", href: "/explore" },
    {
      figure: `${oos.within_25pct ?? 0} of ${oos.n}`,
      label: `blind predictions within 25% of the published score (median miss ${oos.median_abs_error.toFixed(1)}%)`,
      href: "/methods",
    },
    {
      figure: tracker.bills.toLocaleString("en-US"),
      label: updated ? `bills in Congress tracked, updated ${updated}` : "bills in Congress tracked",
      href: "/tracker",
    },
    { figure: String(m.social_security_options), label: "Social Security options and their trust fund effects", href: "/social-security" },
  ];
}
