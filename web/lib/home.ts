import { evidence, manifest, preset, presets, scorecardEntries, tierOf, type Tier } from "./data";
import { DEFAULT_PAIR } from "./compare";
import { shortLabel } from "./format";
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

/**
 * The proposals the home page's live compare may show: those whose figure reads
 * off the out-of-sample tier, either through a pre-registered row of their own
 * or through their class's out-of-sample band. Fitted rows and unfitted
 * reconstructions are left out, so the first thing a visitor sees is never a
 * figure that agrees by construction (C1's rule).
 */
export type HomeCandidate = { id: string; name: string; basis: string };

export function homeCandidates(): HomeCandidate[] {
  return presets().flatMap((info) => {
    const cred = preset(info.id)?.conventional.credibility;
    if (!cred) return [];
    const own = cred.own_row_tier;
    if (own === "out_of_sample") {
      return [{ id: info.id, name: shortLabel(info.name), basis: "out-of-sample, its own pre-registered row" }];
    }
    if (!own && cred.n_tier1_rows > 0) {
      return [{ id: info.id, name: shortLabel(info.name), basis: `out-of-sample, class band of ${cred.n_tier1_rows} rows` }];
    }
    return [];
  });
}

/** The pair the home page shows: the default first proposal, and ``vs`` when it is a candidate. */
export function homePair(vs: string | string[] | undefined): [string, string] {
  const first: string = DEFAULT_PAIR[0];
  const wanted = Array.isArray(vs) ? vs[0] : vs;
  const allowed = homeCandidates().map((c) => c.id).filter((id) => id !== first);
  const second = wanted && allowed.includes(wanted) ? wanted : DEFAULT_PAIR[1];
  return [first, second];
}

/** The one-line trust strip under the example. The count is the export's, so it cannot go stale. */
export function trustStrip(): { count: number; text: string } {
  const n = evidence().out_of_sample.n;
  return { count: n, text: `${n} held-out benchmark cases; accuracy varies by policy type.` };
}

export type StartingPoint = { question: string; href: string; answer: string };

/** Three questions in place of the section directory, each opening a page already set up to answer it. */
export const STARTING_POINTS: StartingPoint[] = [
  {
    question: "Which policies reduce the deficit?",
    href: "/explore?show=reduces&sort=size",
    answer: "Every proposal that cuts the deficit, largest first.",
  },
  {
    question: "What would it take to pay for a proposal?",
    href: "/build?values=deficit-hawk",
    answer: "A package built toward a deficit target, with the gap still to close.",
  },
  {
    question: "Which Social Security changes close the gap?",
    href: "/social-security",
    answer: "The actuaries' options, and how far each goes toward 75-year solvency.",
  },
];
