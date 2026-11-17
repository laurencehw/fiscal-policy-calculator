// A preset's curated legal status (fiscal_model/policy_status.py), as the site shows it.
import type { LawStatus } from "./types";

/** Statuses worth a chip in a list. "Proposed" is the default reading, so lists leave it out. */
export function chipWorthy(status: LawStatus | null | undefined): status is LawStatus {
  return Boolean(status && status.status !== "proposed");
}

/** The short chip text. A pre-2025-law score says so, since that is what changes how to read it. */
export function chipText(status: LawStatus): string {
  if (status.status === "superseded") return "Superseded by P.L. 119-21";
  if (status.status === "partially") return status.pre_2025_law ? "Scored against pre-2025 law" : "Partly overtaken since proposed";
  if (status.status === "enacted") return "Already law";
  return "Proposed, not enacted";
}

/** The eyebrow over a proposal: its window and the law it is measured against. */
export function baselineEyebrow(window: string, vintage: string, status: LawStatus | null | undefined): string {
  if (status?.pre_2025_law) return `${window} · scored against pre-2025 law, not the CBO ${vintage} baseline`;
  return `${window} · CBO ${vintage} baseline`;
}
