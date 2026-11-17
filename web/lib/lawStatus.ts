// A preset's curated legal status (fiscal_model/policy_status.py), as the site shows it.
import { money } from "./format";
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

/**
 * The figure a pre-2025-law preset scores on the current-law baseline, or null when
 * it has none: $0 when already law, another preset's stored score when it is the same
 * question, and null when the remainder is not computed. `storedScore` looks up a
 * preset's stored conventional score by id.
 */
export function currentLawFigure(
  status: LawStatus | null | undefined,
  storedScore: (id: string) => number | null,
): number | null {
  const answer = status?.pre_2025_law ? status.current_law : null;
  if (!answer) return null;
  if (answer.kind === "already_law") return 0;
  if (answer.kind === "same_as" && answer.same_as) return storedScore(answer.same_as);
  return null;
}

/** A short line for a list: what the preset scores on current law. */
export function currentLawLine(status: LawStatus | null | undefined, figure: number | null): string | null {
  const answer = status?.pre_2025_law ? status.current_law : null;
  if (!answer) return null;
  if (answer.kind === "already_law") return "$0 on current law: already law";
  if (figure !== null) return `${money(figure)} on current law`;
  return "Not scored on current law";
}
