// Choosing which proposals to set beside each other, and whether a difference is honest.
import { zeroAxis } from "./chartaxis";

export const MAX_COMPARE = 3;

/**
 * The only shipped preset whose own scorecard row is an out-of-sample prediction.
 * U6 should open on this one. A second out-of-sample preset does not exist, and
 * the corporate presets are fitted, so they are not a stand-in for the empty slot.
 */
export const OUT_OF_SAMPLE_PRESET_IDS = ["top-rate-39-6"] as const;

export type ComparePoint = { window: string; baseline: string; name: string };

export function selectIds(
  raw: string | null | undefined,
  known: ReadonlySet<string>,
): { ids: string[]; unknown: string[]; refused: string[] } {
  const seen = new Set<string>();
  const ids: string[] = [];
  const unknown: string[] = [];
  const refused: string[] = [];
  for (const part of (raw ?? "").split(",")) {
    const id = part.trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    if (!known.has(id)) {
      unknown.push(id);
      continue;
    }
    if (ids.length >= MAX_COMPARE) {
      refused.push(id);
      continue;
    }
    ids.push(id);
  }
  return { ids, unknown, refused };
}

export function unknownSentence(ids: string[]): string {
  if (ids.length === 0) return "";
  const list = ids.join(", ");
  return ids.length === 1
    ? `I dropped ${list}. It is not a proposal on this site.`
    : `I dropped ${list}. They are not proposals on this site.`;
}

export function refusedSentence(ids: string[]): string {
  if (ids.length === 0) return "";
  return `I left off ${ids.join(", ")}. This page compares three proposals at a time.`;
}

/** One axis for every series, running through zero and past the largest bar. */
export function sharedDomain(series: number[][]): { low: number; high: number; ticks: number[] } {
  const ticks = zeroAxis(series.flat()).ticks;
  return { low: ticks[0] ?? 0, high: ticks[ticks.length - 1] ?? 0, ticks };
}

export function differenceNote(items: ComparePoint[]): { draw: boolean; text: string } {
  if (items.length !== 2) {
    return {
      draw: false,
      text: items.length > 2 ? "I do not draw a difference across three proposals." : "",
    };
  }
  const [a, b] = items;
  if (a.window !== b.window || a.baseline !== b.baseline) {
    return {
      draw: false,
      text: `I do not draw a difference. ${a.name} is scored on ${a.window}, ${a.baseline}, and ${b.name} is scored on ${b.window}, ${b.baseline}.`,
    };
  }
  return { draw: true, text: "" };
}

export function differenceYears(
  a: { year: number; value: number }[],
  b: { year: number; value: number }[],
): { year: number; value: number }[] | null {
  if (a.length !== b.length || a.some((row, i) => row.year !== b[i]?.year)) return null;
  return a.map((row, i) => ({ year: row.year, value: row.value - b[i].value }));
}
