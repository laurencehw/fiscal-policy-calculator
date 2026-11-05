// One identity for every figure: who produced it, which kind of estimate it is,
// the window, the baseline, and the tier. The tag text is `identityLine`.
import type { Credibility } from "./types";

export type IdentityKind = "model" | "model-dynamic" | "published" | "package-sum";

export type EstimateIdentity = {
  producer: string;
  kind: IdentityKind;
  window: string;
  baseline: string;
  tier: string;
  tierLabel: string;
  limitation: string;
};

/** A scored result, plus the published producer when the figure is not ours. */
export type IdentityResult = {
  budget_window?: string;
  baseline_vintage?: string;
  credibility?: Credibility | null;
  cbo_source?: string | null;
};

const TIER_LABELS: Record<string, string> = {
  fitted: "Calibrated reference",
  reconstruction: "Unfitted reconstruction",
  out_of_sample: "Out-of-sample prediction",
  none: "no published benchmark",
};

const MONTHS: Record<string, string> = {
  january: "Jan",
  february: "Feb",
  march: "Mar",
  april: "Apr",
  may: "May",
  june: "Jun",
  july: "Jul",
  august: "Aug",
  september: "Sep",
  october: "Oct",
  november: "Nov",
  december: "Dec",
};

const KIND_WORD: Record<IdentityKind, string> = {
  model: "conventional",
  "model-dynamic": "with macroeconomic feedback",
  published: "published",
  "package-sum": "sum of standalone published scores",
};

/** "February 2026" → "CBO Feb 2026 baseline". Empty when the vintage is unknown. */
export function baselinePhrase(vintage: string | undefined): string {
  const text = (vintage ?? "").trim();
  if (!text) return "";
  const [month, year] = text.split(/\s+/);
  const short = MONTHS[month.toLowerCase()];
  if (short && year) return `CBO ${short} ${year} baseline`;
  return `CBO ${text} baseline`;
}

function resolveTier(cred: Credibility | null | undefined): { tier: string; tierLabel: string; limitation: string } {
  if (!cred) {
    return { tier: "none", tierLabel: "", limitation: "The tier is named on each proposal." };
  }
  const own = cred.own_row_tier?.trim();
  if (own) {
    const tierLabel = cred.own_row_tier_label?.trim() || TIER_LABELS[own] || own;
    return { tier: own, tierLabel, limitation: limitationForTier(own, cred) };
  }
  const n = cred.n_tier1_rows ?? 0;
  if (n > 0) {
    return {
      tier: "out_of_sample",
      tierLabel: `out-of-sample, n=${n}`,
      limitation: `No row of its own. The class band is ${n} out-of-sample cases.`,
    };
  }
  return {
    tier: "none",
    tierLabel: TIER_LABELS.none,
    limitation: cred.no_band_reason || "No published benchmark is scored against this policy.",
  };
}

function limitationForTier(tier: string, cred: Credibility): string {
  if (tier === "fitted") return "Calibrated to a published score. Agreement is by construction, not an independent test.";
  if (tier === "out_of_sample") return "Pre-registered out-of-sample prediction.";
  if (tier === "reconstruction") return "Unfitted reconstruction. No constant is fitted to this figure.";
  return cred.limitations[0] ?? "";
}

/**
 * Identity of one figure. `kind` selects the producer and the words in the tag.
 * The tier is the scorecard's own row when there is one; otherwise the class
 * band (out of sample, with its n) or none.
 */
export function estimateIdentity(result: IdentityResult, kind: IdentityKind): EstimateIdentity {
  if (kind === "package-sum") {
    return {
      producer: "Published scores",
      kind,
      window: "",
      baseline: "",
      tier: "none",
      tierLabel: "",
      limitation: "Sum of standalone published scores. Interactions between these policies are not measured.",
    };
  }
  const { tier, tierLabel, limitation } = resolveTier(result.credibility);
  if (kind === "published") {
    // The tier describes this calculator's figure against the published one, not
    // the published figure itself: "Treasury · published · Calibrated reference"
    // would read as Treasury's number being calibrated. The tier stays on the
    // record for code; the tag names only the producer.
    return {
      producer: result.cbo_source?.trim() || "Published",
      kind,
      window: "",
      baseline: "",
      tier,
      tierLabel: "",
      limitation: result.credibility ? limitation : "The producer is named on each proposal.",
    };
  }
  if (kind === "model-dynamic") {
    // The scorecard's tiers grade conventional scores. A fitted conventional row
    // does not make the dynamic figure calibrated, and the dynamic tier (B6) is
    // never pooled with the conventional one.
    return {
      producer: "This calculator",
      kind,
      window: result.budget_window?.trim() ?? "",
      baseline: baselinePhrase(result.baseline_vintage),
      tier: "none",
      tierLabel: "not benchmarked",
      limitation: "The macroeconomic feedback is not scored against a published dynamic estimate here.",
    };
  }
  return {
    producer: "This calculator",
    kind,
    window: result.budget_window?.trim() ?? "",
    baseline: baselinePhrase(result.baseline_vintage),
    tier,
    tierLabel,
    limitation,
  };
}

/** The same identity with the tier left off, for a figure the tier does not grade. */
export function withoutTier(identity: EstimateIdentity): EstimateIdentity {
  return { ...identity, tierLabel: "" };
}

/** The long form a reader sees, with empty parts left out. */
export function identityLine(identity: EstimateIdentity): string {
  const word = KIND_WORD[identity.kind];
  // "Published · published" says nothing twice; drop the kind word when the producer already is it.
  const kindPart = word.toLowerCase() === identity.producer.trim().toLowerCase() ? "" : word;
  return [identity.producer, kindPart, identity.window, identity.baseline, identity.tierLabel]
    .filter((part) => part.length > 0)
    .join(" · ");
}

/** The short form for a table cell: "calc.", "Treasury", "sum". */
export function shortProducer(identity: EstimateIdentity): string {
  if (identity.kind === "model" || identity.kind === "model-dynamic") return "calc.";
  if (identity.kind === "package-sum") return "sum";
  const name = identity.producer.trim();
  if (/^published$/i.test(name)) return "published";
  if (/treasury/i.test(name)) return "Treasury";
  if (/joint committee|^jct\b/i.test(name)) return "JCT";
  if (/penn wharton|\bpwbm\b/i.test(name)) return "PWBM";
  if (/tax foundation/i.test(name)) return "Tax Foundation";
  if (/^cbo\b/i.test(name)) return "CBO";
  if (/congressional research|^crs\b/i.test(name)) return "CRS";
  const brief = name.split(/[/;(]/)[0].trim();
  return brief.length > 22 ? `${brief.slice(0, 20)}…` : brief;
}
