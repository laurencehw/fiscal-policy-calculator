import type { Metadata } from "next";
import { PackageBuilder } from "@/components/PackageBuilder";
import { buildCatalog, manifest, preset, valuesArchetypes } from "@/lib/data";
import { ARCHIVED_AREA } from "@/lib/lawStatus";
import { againstPre2025Law, estimateIdentity, type EstimateIdentity } from "@/lib/identity";
import { siteUrl } from "@/lib/site";
import { StaleLink } from "@/components/StaleLink";

export const metadata: Metadata = {
  title: "Build",
  description: "Put policies together and see what the package does to the ten-year deficit.",
};

export default function Build() {
  const rows = buildCatalog();
  // Illustrative reconstructions come after the live areas, as in the app, and presets
  // scored against pre-2025 law come last, in their own archived group.
  const archived = rows.filter((r) => r.area === ARCHIVED_AREA);
  const live = rows.filter((r) => r.area !== ARCHIVED_AREA);
  const ordered = [...live.filter((r) => !r.illustrative), ...live.filter((r) => r.illustrative), ...archived];
  // The calculator's own ten-year conventional score, for rows that are also Explore presets.
  const calculator: Record<string, number> = {};
  const identities: Record<string, { published: EstimateIdentity; model: EstimateIdentity | null }> = {};
  const frame = manifest();
  const site = {
    budget_window: frame.budget_windows[0] ?? "",
    baseline_vintage: frame.baseline_vintages[0] ?? "",
  };
  for (const row of ordered) {
    const scored = preset(row.build_id)?.conventional ?? null;
    if (scored && typeof scored.ten_year_deficit_impact === "number") calculator[row.build_id] = scored.ten_year_deficit_impact;
    // "Published" only when someone outside this repository published the figure.
    const kind = row.cbo_published === false ? "unpublished" : "published";
    const model = scored ? estimateIdentity(scored, "model") : null;
    identities[row.build_id] = {
      published: estimateIdentity(scored ? { ...scored, cbo_source: row.source } : { ...site, credibility: null, cbo_source: row.source }, kind),
      model: model && row.status?.pre_2025_law ? againstPre2025Law(model) : model,
    };
  }
  return (
    <div className="work">
      <header>
        <span className="eyebrow">Build</span>
        <h1>Build a package</h1>
        <p className="sentence">
          Each row is a ten-year list price, published unless it is tagged otherwise, and where I also score the
          policy I show that conventional estimate under the name.
        </p>
        <p className="note">
          A tick that conflicts with one already ticked swaps them. A positive figure adds to the deficit and a
          negative one reduces it.
        </p>
        <StaleLink scoresDate={frame.scores_date ?? ""} />
      </header>
      <PackageBuilder
        rows={ordered}
        calculator={calculator}
        identities={identities}
        packageIdentity={estimateIdentity(site, "package-sum")}
        archetypes={valuesArchetypes()}
        scoresDate={frame.scores_date ?? ""}
        site={siteUrl()}
      />
    </div>
  );
}
