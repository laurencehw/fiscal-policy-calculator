// Build's second total (bet 4): the calculator's own conventional scores for the
// ticked rows, all on one window and one baseline, with the one overlap the CPS
// microsim measures applied, and plain sentences about every other pair. The
// list-price sum stays the headline; this sits beside it.
//
// Everything comes from site_data/package-joint.json, which export_static.py
// writes from fiscal_model/package_interactions.py. Nothing here invents a
// number: a measured overlap is a share of the reference member's own yield,
// applied to the calculator's score for that member.
import { shortLabel } from "./format";
import type { BuildRow } from "./types";

export type JointPair = {
  a: string;
  b: string;
  kind: "interacting" | "structurally_additive" | "no_overlap" | "unmodelled";
  /** The overlap as a share of the reference member's standalone yield (revenue convention). */
  share: number | null;
  reference: string | null;
};

export type PackageJoint = {
  channels: Record<string, string[]>;
  channel_labels: Record<string, string>;
  measurable: string[];
  pairs: JointPair[];
};

export type Overlap = { a: string; b: string; reference: string; share: number; billions: number };

export type CalculatorTotal = {
  /** Billions over the calculator's window, deficit convention. */
  value: number;
  /** Ticked rows the calculator scores, in catalog order. */
  scored: string[];
  /** Ticked rows it does not score, with their list prices. */
  excluded: { id: string; label: string; score: number }[];
  overlaps: Overlap[];
  /** How many of the scored rows sit in each validation tier. */
  tiers: Record<string, number>;
};

function pairOf(joint: PackageJoint, x: string, y: string): JointPair | undefined {
  const [a, b] = x < y ? [x, y] : [y, x];
  return joint.pairs.find((p) => p.a === a && p.b === b);
}

function ticked(rows: BuildRow[], selected: string[]): BuildRow[] {
  const ids = new Set(selected);
  return rows.filter((r) => ids.has(r.build_id));
}

/**
 * The calculator's total for the ticked rows, or null when there is nothing to
 * show beside the list-price sum (fewer than two policies, or none it scores).
 * `tiers` maps a build id to its scorecard tier; a row with none counts as "none".
 */
export function calculatorTotal(
  rows: BuildRow[],
  selected: string[],
  calculator: Record<string, number>,
  joint: PackageJoint,
  tiers: Record<string, string> = {},
): CalculatorTotal | null {
  const list = ticked(rows, selected);
  if (list.length < 2) return null;
  const scored = list.filter((r) => typeof calculator[r.build_id] === "number").map((r) => r.build_id);
  if (!scored.length) return null;
  const excluded = list
    .filter((r) => !scored.includes(r.build_id))
    .map((r) => ({ id: r.build_id, label: shortLabel(r.label), score: r.score }));
  let value = scored.reduce((sum, id) => sum + calculator[id], 0);
  const overlaps: Overlap[] = [];
  for (let i = 0; i < scored.length; i++) {
    for (let j = i + 1; j < scored.length; j++) {
      const pair = pairOf(joint, scored[i], scored[j]);
      if (!pair || pair.kind !== "interacting" || pair.share === null || !pair.reference) continue;
      // A negative share is less revenue than the two alone, so the deficit is higher.
      const billions = -pair.share * Math.abs(calculator[pair.reference]);
      overlaps.push({ a: pair.a, b: pair.b, reference: pair.reference, share: pair.share, billions });
      value += billions;
    }
  }
  const counts: Record<string, number> = {};
  for (const id of scored) {
    const tier = tiers[id] || "none";
    counts[tier] = (counts[tier] ?? 0) + 1;
  }
  return { value, scored, excluded, overlaps, tiers: counts };
}

/** [one in a count, several in a count, "all are …", "the one is …"] for each scorecard tier. */
const TIER_WORDS: Record<string, [string, string, string, string]> = {
  fitted: ["calibrated to its published figure", "calibrated to their published figures", "calibrated to their published figures", "calibrated to its published figure"],
  out_of_sample: ["out-of-sample prediction", "out-of-sample predictions", "out-of-sample predictions", "an out-of-sample prediction"],
  reconstruction: ["unfitted reconstruction", "unfitted reconstructions", "unfitted reconstructions", "an unfitted reconstruction"],
  retired: ["with a withdrawn target", "with withdrawn targets", "scored against withdrawn targets", "scored against a withdrawn target"],
  none: ["with no published benchmark", "with no published benchmark", "without a published benchmark", "without a published benchmark"],
};

/** Which tiers the scored rows sit in, e.g. "Mixes tiers: 1 out-of-sample prediction, 3 unfitted reconstructions." */
export function tierSentence(tiers: Record<string, number>): string {
  const keys = [...Object.keys(TIER_WORDS), ...Object.keys(tiers).filter((k) => !(k in TIER_WORDS))].filter((k) => tiers[k]);
  const words = (k: string, n: number) => (TIER_WORDS[k] ? TIER_WORDS[k][n === 1 ? 0 : 1] : k);
  if (keys.length === 1) {
    const k = keys[0];
    const n = tiers[k];
    const lead = n === 1 ? "The one I score is" : n === 2 ? "Both are" : `All ${n} are`;
    return `${lead} ${TIER_WORDS[k] ? TIER_WORDS[k][n === 1 ? 3 : 2] : k}.`;
  }
  return `Mixes tiers: ${keys.map((k) => `${tiers[k]} ${words(k, tiers[k])}`).join(", ")}.`;
}

const LIMIT = 3;

function listPairs(names: string[]): string {
  if (names.length <= LIMIT) return names.join("; ");
  return `${names.slice(0, LIMIT).join("; ")}; and ${names.length - LIMIT} more`;
}

/**
 * Plain sentences about how the ticked policies interact, from the microsim's
 * classification. Empty for fewer than two policies. A pair the calculator adds
 * by construction is said to be that, never "no interaction".
 */
export function interactionNotes(rows: BuildRow[], selected: string[], joint: PackageJoint): string[] {
  const list = ticked(rows, selected);
  if (list.length < 2) return [];
  const name = (id: string) => shortLabel(rows.find((r) => r.build_id === id)?.label ?? id);
  const measurable = new Set(joint.measurable);
  const notes: string[] = [];
  const additive: string[] = [];
  const shared: string[] = [];
  let unmodelled = false;
  for (let i = 0; i < list.length; i++) {
    for (let j = i + 1; j < list.length; j++) {
      const x = list[i].build_id;
      const y = list[j].build_id;
      if (measurable.has(x) && measurable.has(y)) {
        const pair = pairOf(joint, x, y);
        if (pair?.kind === "interacting" && pair.share !== null && pair.reference) {
          const pct = Math.abs(pair.share * 100).toFixed(0);
          const way = pair.share < 0 ? "less" : "more";
          notes.push(
            `${name(x)} and ${name(y)} overlap. Scored together on the CPS microsimulation they raise ${way} revenue than the two alone, by about ${pct}% of what ${name(pair.reference)} raises alone. That share is applied in the calculator total.`,
          );
        } else if (pair?.kind === "interacting") {
          notes.push(`${name(x)} and ${name(y)} overlap, and the overlap has not been measured.`);
        } else if (pair?.kind === "structurally_additive") {
          additive.push(`${name(x)} and ${name(y)}`);
        }
        continue;
      }
      unmodelled = true;
      const cx = joint.channels[x] ?? [];
      const both = (joint.channels[y] ?? []).filter((c) => cx.includes(c));
      if (both.length) {
        const what = both.map((c) => joint.channel_labels[c] ?? c).join(", ");
        shared.push(`${name(x)} and ${name(y)} (${what})`);
      }
    }
  }
  if (additive.length) {
    notes.push(
      `${listPairs(additive)} add by construction in this model: the calculator applies one after the other, so it cannot see an overlap. That is not a measurement of zero.`,
    );
  }
  if (shared.length) {
    notes.push(`These act on the same part of the tax code and have no joint model, so their sum is not a joint score: ${listPairs(shared)}.`);
  }
  if (unmodelled) notes.push(shared.length ? "Other interactions are not modelled." : "Interactions between these policies are not modelled.");
  return notes;
}
