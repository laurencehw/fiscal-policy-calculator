import type { Metadata } from "next";
import { PackageBuilder } from "@/components/PackageBuilder";
import { buildCatalog, manifest, preset, valuesArchetypes } from "@/lib/data";
import { estimateIdentity, type EstimateIdentity } from "@/lib/identity";

export const metadata: Metadata = {
  title: "Build",
  description: "Put policies together and see what the package does to the ten-year deficit.",
};

export default function Build() {
  const rows = buildCatalog();
  // Illustrative reconstructions come last, as in the app.
  const ordered = [...rows.filter((r) => !r.illustrative), ...rows.filter((r) => r.illustrative)];
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
    identities[row.build_id] = {
      published: estimateIdentity(scored ? { ...scored, cbo_source: row.source } : { ...site, credibility: null, cbo_source: row.source }, "published"),
      model: scored ? estimateIdentity(scored, "model") : null,
    };
  }
  return (
    <div className="work">
      <header>
        <span className="eyebrow">Build</span>
        <h1>Build a package</h1>
        <p className="sentence">
          Each row is a published ten-year list price, and where I also score the policy I show that conventional
          estimate under the name.
        </p>
        <p className="note">
          A tick that conflicts with one already ticked swaps them. A positive figure adds to the deficit and a
          negative one reduces it.
        </p>
      </header>
      <PackageBuilder
        rows={ordered}
        calculator={calculator}
        identities={identities}
        packageIdentity={estimateIdentity(site, "package-sum")}
        archetypes={valuesArchetypes()}
      />
    </div>
  );
}
