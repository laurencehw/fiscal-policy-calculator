import type { Metadata } from "next";
import { Suspense } from "react";
import { Tailor } from "@/components/Tailor";
import { StaleLink } from "@/components/StaleLink";
import { manifest, preset, presets } from "@/lib/data";
import { TAILOR_SHAPES } from "@/lib/adjust";
import { estimateIdentity } from "@/lib/identity";
import { shortLabel } from "@/lib/format";
import type { PresetMatch } from "@/components/Tailor";

export const metadata: Metadata = {
  title: "Tailor",
  description: "Score your own income or corporate tax rate change over ten years.",
};

export default function TailorPage() {
  const scoresDate = manifest().scores_date ?? "";
  // The presets Tailor can reproduce, with what their pages say about the published score.
  const index = presets();
  const matches: Record<string, PresetMatch> = {};
  for (const id of Object.keys(TAILOR_SHAPES)) {
    const file = preset(id);
    const info = index.find((row) => row.id === id);
    if (!file || !info) continue;
    const c = file.conventional;
    matches[id] = {
      id,
      name: shortLabel(info.name),
      tenYear: c.ten_year_deficit_impact,
      credibility: c.credibility,
      published:
        info.cbo_published && info.cbo_source ? estimateIdentity({ ...c, cbo_source: info.cbo_source }, "published") : null,
    };
  }
  return (
    <div className="work">
      <header>
        <span className="eyebrow">Tailor</span>
        <h1>Score your own rate change</h1>
        <p className="sentence">
          Raise or cut an income or corporate rate, and the engine scores the ten-year deficit effect.
        </p>
        <p className="note">
          The engine can also score capital gains rates, spending changes and phase-ins, and I plan to add those to this
          page.
        </p>
        <StaleLink scoresDate={scoresDate} />
      </header>
      <Suspense>
        <Tailor scoresDate={scoresDate} presetMatches={matches} />
      </Suspense>
    </div>
  );
}
