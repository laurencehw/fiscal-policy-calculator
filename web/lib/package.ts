// Build's package rules, as in the app's deficit_target tab: one policy per
// exclusive group, and a policy that already contains another hides it.
import type { BuildRow } from "./types";

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
