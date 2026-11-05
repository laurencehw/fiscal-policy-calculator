// Build's package rules, as in the app's deficit_target tab: one policy per
// exclusive group, and a policy that already contains another hides it.
import type { BuildRow } from "./types";

/** Add ``id``, and name anything the exclusive-group rules dropped. */
export function addToPackage(
  rows: BuildRow[],
  selected: string[],
  id: string,
): { selected: string[]; replaced: string[] } {
  const next = choose(rows, selected, id);
  return { selected: next, replaced: replacedBy(rows, selected, next).dropped };
}

/** One tick that swapped policies out, kept so it can be undone. */
export type Replacement = { added: string; dropped: string[] };

/**
 * What a change from ``before`` to ``after`` replaced: the policy it added and
 * the ones the package rules dropped to make room. A plain untick, or a tick
 * that drops nothing, replaced nothing and returns an empty ``dropped``.
 */
export function replacedBy(rows: BuildRow[], before: string[], after: string[]): Replacement & { added: string | null } {
  const known = new Set(rows.map((r) => r.build_id));
  const added = after.filter((id) => !before.includes(id) && known.has(id));
  if (added.length !== 1) return { added: added[0] ?? null, dropped: [] };
  return { added: added[0], dropped: before.filter((id) => !after.includes(id) && known.has(id)) };
}

/**
 * Undo a replacement: take the added policy out and put back what it dropped.
 * Edits made since are kept, and the package rules are applied again, so an
 * undo never leaves two alternatives ticked together.
 */
export function undoReplacement(rows: BuildRow[], selected: string[], change: Replacement): string[] {
  let next = selected.filter((id) => id !== change.added);
  for (const id of change.dropped) {
    if (!covered(rows, next).has(id)) next = choose(rows, next, id);
  }
  return next;
}

/** The policies in the package with their published figures, in catalog order, and the scale their bars share. */
export function contributions(rows: BuildRow[], selected: string[]): { rows: BuildRow[]; scale: number } {
  const chosen = new Set(selected);
  const list = rows.filter((r) => chosen.has(r.build_id));
  return { rows: list, scale: Math.max(1, ...list.map((r) => Math.abs(r.score))) };
}

/**
 * How far a package goes toward a philosophy's target. ``gap`` is the deficit
 * reduction the target needs (positive); ``sum`` is the package in the deficit
 * convention, so a package that reduces the deficit is negative.
 */
export function towardTarget(sum: number, gap: number): { share: number; remaining: number } {
  if (gap <= 0) return { share: 0, remaining: 0 };
  return { share: -sum / gap, remaining: gap + sum };
}

/** Add ``id`` to the package, dropping anything it conflicts with or contains. */
export function choose(rows: BuildRow[], selected: string[], id: string): string[] {
  const row = rows.find((r) => r.build_id === id);
  if (!row) return selected;
  const groups = new Set(row.exclusive_groups);
  const kept = selected.filter((other) => {
    if (other === id) return false;
    const o = rows.find((r) => r.build_id === other);
    if (!o) return false;
    if (o.exclusive_groups.some((g) => groups.has(g))) return false;
    if (row.subsumes.includes(other)) return false;
    return true;
  });
  return [...kept, id];
}

/** Ids the package already contains through a broader policy, with the policy that contains each. */
export function covered(rows: BuildRow[], selected: string[]): Map<string, string> {
  const out = new Map<string, string>();
  for (const id of selected) {
    const row = rows.find((r) => r.build_id === id);
    for (const sub of row?.subsumes ?? []) out.set(sub, id);
  }
  return out;
}

/** Sum of list prices, in catalog order of the ids that exist. */
export function total(rows: BuildRow[], selected: string[]): number {
  const chosen = new Set(selected);
  return rows.filter((r) => chosen.has(r.build_id)).reduce((sum, r) => sum + r.score, 0);
}

/** ``?policies=a,b`` as the app writes it; unknown ids are dropped and rules re-applied. */
export function fromQuery(rows: BuildRow[], value: string | null): string[] {
  let selected: string[] = [];
  for (const id of (value ?? "").split(",").map((s) => s.trim()).filter(Boolean)) {
    if (!covered(rows, selected).has(id)) selected = choose(rows, selected, id);
  }
  return selected;
}

/** How far the calculator's own score sits from a row's published list price, before Build calls it out. */
export const DIFFERS_AT = 0.25;

/**
 * The calculator's score beside a published one: its share apart, and whether the
 * gap is wide enough (or the sign opposite) that a reader should be told.
 */
export function calculatorGap(published: number, calculator: number): { share: number; differs: boolean } {
  if (published === 0) return { share: calculator === 0 ? 0 : Infinity, differs: calculator !== 0 };
  const share = Math.abs(calculator - published) / Math.abs(published);
  const flipped = Math.sign(calculator) !== Math.sign(published) && calculator !== 0;
  return { share, differs: flipped || share >= DIFFERS_AT };
}
