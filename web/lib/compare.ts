// Compare: up to three proposals side by side, as plain data so it can be tested
// without a page. The page reads ids from the URL, these functions decide which
// ids stand, the shared axis, and whether a difference can be stated.
import { zeroAxis } from "./chartaxis";
import { money } from "./format";

export const MAX_COMPARE = 3;

/**
 * The pair the home page opens on (U6). Both read off the out-of-sample tier:
 * the 39.6% top rate has its own pre-registered row, and the 45% top rate sits
 * in the same eleven-row class. The corporate presets are not used because the
 * 28% row is fitted, so agreement there is by construction.
 */
export const DEFAULT_PAIR = ["top-rate-39-6", "top-rate-45"] as const;

export type CompareYear = { year: number; value: number };

export type CompareItem = {
  id: string;
  name: string;
  window: string;
  baseline: string;
  tenYear: number;
  years: CompareYear[];
};

export type ParsedIds = {
  /** Ids that name a proposal, in the order given, at most three. */
  ids: string[];
  /** Ids that name no proposal. */
  unknown: string[];
  /** Known ids past the third, which the page does not show. */
  refused: string[];
};

/** `?ids=a,b,c` (or repeated `ids=`) into the ids that stand, with the rest named. */
export function parseIds(raw: string | string[] | undefined, known: ReadonlySet<string>): ParsedIds {
  const parts = (Array.isArray(raw) ? raw : [raw ?? ""])
    .flatMap((value) => value.split(","))
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean);
  const ids: string[] = [];
  const unknown: string[] = [];
  const refused: string[] = [];
  for (const id of parts) {
    if (ids.includes(id) || unknown.includes(id) || refused.includes(id)) continue;
    if (!known.has(id)) unknown.push(id);
    else if (ids.length >= MAX_COMPARE) refused.push(id);
    else ids.push(id);
  }
  return { ids, unknown, refused };
}

/** The page's URL for a set of ids. An empty set is the bare page. */
export function compareHref(ids: readonly string[]): string {
  return ids.length ? `/compare?ids=${ids.slice(0, MAX_COMPARE).join(",")}` : "/compare";
}

/** Add or remove one id. Adding a fourth returns the set unchanged. */
export function toggleId(ids: readonly string[], id: string): string[] {
  if (ids.includes(id)) return ids.filter((other) => other !== id);
  if (ids.length >= MAX_COMPARE) return [...ids];
  return [...ids, id];
}

/** One y-axis for every small multiple, so equal heights mean equal dollars. */
export function sharedAxis(items: readonly CompareItem[]): { lo: number; hi: number; ticks: number[] } {
  const values = items.flatMap((item) => item.years.map((row) => row.value));
  const { ticks } = zeroAxis(values.length ? values : [0]);
  return { lo: ticks[0], hi: ticks[ticks.length - 1], ticks };
}

export type Difference =
  | { drawn: true; sentence: string; billions: number }
  | { drawn: false; reason: string };

/**
 * A difference is stated only for exactly two proposals scored on the same
 * window and baseline. Three figures are never totalled or differenced: they
 * are alternatives or separate policies, and a sum would claim an interaction
 * nobody has scored.
 */
export function difference(items: readonly CompareItem[]): Difference {
  if (items.length !== 2) {
    return {
      drawn: false,
      reason:
        items.length > 2
          ? "With three proposals I show each on its own and draw no difference or total; pick two to see the gap between them."
          : "Add a second proposal to see the gap between two ten-year figures.",
    };
  }
  const [a, b] = items;
  if (a.window !== b.window) {
    return {
      drawn: false,
      reason: `These two are scored on different windows (${a.window} and ${b.window}), so I do not subtract one from the other.`,
    };
  }
  if (a.baseline !== b.baseline) {
    return {
      drawn: false,
      reason: `These two are scored on different baselines (${a.baseline} and ${b.baseline}), so I do not subtract one from the other.`,
    };
  }
  const billions = b.tenYear - a.tenYear;
  const gap = money(Math.abs(billions)).replace(/^[+-]/, "");
  const sentence =
    billions === 0
      ? `${a.name} and ${b.name} have the same ten-year effect on the deficit, ${a.window}.`
      : `Over ${a.window}, ${b.name} leaves the deficit ${gap} ${billions > 0 ? "higher" : "lower"} than ${a.name} does. Each is scored on its own, so this is the gap between two standalone figures, not the effect of doing both.`;
  return { drawn: true, sentence, billions };
}

/** Sentences naming the ids the page dropped, or nothing when every id stood. */
export function droppedSentences(parsed: ParsedIds): string[] {
  const lines: string[] = [];
  if (parsed.unknown.length) {
    const list = parsed.unknown.map((id) => `"${id}"`).join(", ");
    lines.push(`No proposal is called ${list}, so ${parsed.unknown.length === 1 ? "it is" : "they are"} left out.`);
  }
  if (parsed.refused.length) {
    const list = parsed.refused.map((id) => `"${id}"`).join(", ");
    lines.push(`The page compares at most ${MAX_COMPARE} proposals, so ${list} ${parsed.refused.length === 1 ? "is" : "are"} left out.`);
  }
  return lines;
}
