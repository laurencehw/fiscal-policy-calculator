// Frozen assignment links, in the Streamlit app's spelling: a Tailor link plus
// ``frozen=1&baseline=<vintage token>``. The settings are locked so a whole class
// gets one set of numbers, and a link frozen on a baseline the site no longer
// serves is refused rather than scored on a different one.

/** "February 2026" or "CBO Feb 2026" to the link token, as share_links.baseline_vintage_token does. */
export function vintageToken(vintage: string): string {
  let text = vintage.trim().toLowerCase();
  if (text.startsWith("cbo")) text = text.slice(3);
  return text.replace(/[^a-z0-9]/g, "");
}

export type Frozen = { frozen: false } | { frozen: true; baseline: string };

export function frozenFrom(params: URLSearchParams): Frozen {
  const on = ["1", "true", "yes", "on"].includes((params.get("frozen") ?? "").trim().toLowerCase());
  if (!on) return { frozen: false };
  return { frozen: true, baseline: (params.get("baseline") ?? "").trim().toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 40) };
}

/** Why a frozen link cannot be honoured against the vintage the engine scored, or null. */
export function frozenRefusal(frozen: Frozen, scoredVintage: string): string | null {
  if (!frozen.frozen) return null;
  if (!frozen.baseline) {
    return "This assignment link is marked frozen but names no baseline, so there is nothing to pin the numbers to. Ask your instructor for a link made from a scored result.";
  }
  if (frozen.baseline !== vintageToken(scoredVintage)) {
    return `This assignment was frozen on a different baseline (${frozen.baseline}); the site now scores on CBO's ${scoredVintage} baseline. The numbers would not be the ones your instructor saw, so nothing is shown. Ask for a link rebuilt on the current baseline.`;
  }
  return null;
}

/** The frozen link for a scored run: its own query plus the lock and the vintage it was scored on. */
export function frozenQuery(query: string, scoredVintage: string): string {
  const params = new URLSearchParams(query);
  params.delete("classroom");
  params.set("frozen", "1");
  params.set("baseline", vintageToken(scoredVintage));
  return params.toString();
}
