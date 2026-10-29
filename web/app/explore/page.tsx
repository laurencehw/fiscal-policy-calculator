import type { Metadata } from "next";
import { ExploreList } from "@/components/ExploreList";
import { manifest, preset, presetsByArea } from "@/lib/data";
import type { ExploreRow } from "@/lib/explore";
import { shortLabel } from "@/lib/format";

export const metadata: Metadata = {
  title: "Explore",
  description: "Every preset proposal, with its ten-year deficit effect.",
};

export default function Explore() {
  const m = manifest();
  const rows: ExploreRow[] = presetsByArea().flatMap((group) =>
    group.presets.map((info) => ({
      id: info.id,
      name: shortLabel(info.name),
      area: group.area,
      conventional: preset(info.id)?.conventional.ten_year_deficit_impact ?? null,
      published: info.cbo_score !== null && info.cbo_published ? info.cbo_score : null,
    })),
  );
  return (
    <>
      <header>
        <span className="eyebrow">Explore</span>
        <h1>Proposals</h1>
        <p className="sentence">
          Ten-year conventional deficit effects, {m.budget_windows.join(", ")}. The first column is this
          calculator&apos;s score; the second is the published score it is checked against, where one exists. A
          positive figure adds to the deficit; a negative one reduces it. Bars share one scale.
        </p>
      </header>
      <ExploreList rows={rows} />
    </>
  );
}
