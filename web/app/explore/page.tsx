import type { Metadata } from "next";
import { ExploreList } from "@/components/ExploreList";
import { manifest, preset, presetsByArea } from "@/lib/data";
import type { ExploreRow } from "@/lib/explore";
import { shortLabel } from "@/lib/format";
import { estimateIdentity } from "@/lib/identity";

export const metadata: Metadata = {
  title: "Explore",
  description: "Every preset proposal, with its ten-year deficit effect.",
};

export default function Explore() {
  const m = manifest();
  const frame = { budget_window: m.budget_windows[0] ?? "", baseline_vintage: m.baseline_vintages[0] ?? "", credibility: null };
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
    <div className="work">
      <header>
        <span className="eyebrow">Explore</span>
        <h1>Proposals</h1>
        <p className="sentence">
          Ten-year conventional deficit effects, {m.budget_windows.join(", ")}, with this calculator&apos;s score
          beside the published score where one exists.
        </p>
      </header>
      <ExploreList
        rows={rows}
        calculator={estimateIdentity(frame, "model")}
        published={estimateIdentity({ cbo_source: "Published", credibility: null }, "published")}
      />
    </div>
  );
}
