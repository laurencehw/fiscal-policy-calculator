import { manifest, preset, presets } from "./data";
import { money, shortLabel } from "./format";

/** The three rows the homepage shows. Dollars are read from the nightly export. */
export const WORKED_PRESET_IDS = ["tcja-full-extension", "corporate-28pct", "ss-donut-250k"] as const;

export type WorkedRow = {
  id: string;
  name: string;
  href: string;
  conventional: number;
  published: number;
  source: string;
};

export function workedRows(): WorkedRow[] {
  const byId = new Map(presets().map((info) => [info.id, info]));
  return WORKED_PRESET_IDS.map((id) => {
    const info = byId.get(id);
    const file = preset(id);
    if (!info || !file || info.cbo_score === null || !info.cbo_published) {
      throw new Error(`worked preset ${id} is missing a conventional score or a published score`);
    }
    return {
      id,
      name: shortLabel(info.name),
      href: `/explore/${id}`,
      conventional: file.conventional.ten_year_deficit_impact,
      published: info.cbo_score,
      source: info.cbo_source ?? "published score",
    };
  });
}

/** Prose under the title. The two figures on a row are different quantities. */
export function homeSectionParagraphs(): string[] {
  const m = manifest();
  return [
    m.sign_convention,
    `The baseline is CBO's ${m.baseline_vintages.join(" and ")} vintage, and the window is ${m.budget_windows.join(", ")}.`,
    "The first figure is this calculator's conventional ten-year estimate. The second is the published score the same policy is checked against. They are different quantities. Explore lists the calculator's score. Build lists the published list price. The calculator is not retuned to make them match, and a gap is a finding rather than a rounding error.",
  ];
}

export function homeRowLine(row: WorkedRow): string {
  return `${row.name}: calculator ${money(row.conventional)}; published ${money(row.published)} (${row.source}).`;
}

export function homeSectionText(): string {
  const rows = workedRows().map(homeRowLine);
  return ["How to read a figure", ...homeSectionParagraphs(), ...rows].join(" ");
}
