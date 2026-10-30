import type { Metadata } from "next";
import { PackageBuilder } from "@/components/PackageBuilder";
import { buildCatalog, preset, presets, valuesArchetypes } from "@/lib/data";

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
  for (const p of presets()) {
    const score = preset(p.id)?.conventional.ten_year_deficit_impact;
    if (typeof score === "number") calculator[p.id] = score;
  }
  return (
    <>
      <header>
        <span className="eyebrow">Build</span>
        <h1>Build a package</h1>
        <p className="sentence">
          Each policy carries a ten-year score, most of them published by CBO, JCT, Treasury or a research group;
          the source is named under each. The figure on each row is that published list price. Where this calculator also scores the policy, its
          conventional estimate is shown under the row, with a flag where the two are a quarter or more apart; the
          link opens the calculator&apos;s full result. Ticking one that conflicts with another swaps them. A positive figure adds to the deficit; a negative one reduces it.
        </p>
      </header>
      <PackageBuilder rows={ordered} calculator={calculator} archetypes={valuesArchetypes()} />
    </>
  );
}
