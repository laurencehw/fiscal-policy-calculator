// Server-only: the Compare cards for a list of ids, read from the nightly export.
// The Compare page and the home page's live compare both build from this.
import type { CompareCard } from "@/components/Compare";
import { preset, presets } from "./data";
import { shortLabel } from "./format";
import { estimateIdentity } from "./identity";

export function compareCards(ids: string[]): CompareCard[] {
  const index = presets();
  return ids.flatMap((id) => {
    const file = preset(id);
    if (!file) return [];
    const c = file.conventional;
    const info = index.find((row) => row.id === id);
    const published =
      info && info.cbo_published && info.cbo_score !== null && info.cbo_source
        ? {
            value: info.cbo_score,
            identity: estimateIdentity({ ...c, cbo_source: info.cbo_source }, "published"),
            date: info.cbo_date,
          }
        : null;
    return [
      {
        item: {
          id,
          name: shortLabel(c.policy_name),
          window: c.budget_window,
          baseline: c.baseline_vintage,
          tenYear: c.ten_year_deficit_impact,
          years: c.year_by_year.map((row) => ({ year: row.year, value: row.final_effect })),
        },
        calculator: estimateIdentity(c, "model"),
        published,
      },
    ];
  });
}
