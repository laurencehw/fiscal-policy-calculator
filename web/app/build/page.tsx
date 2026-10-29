import type { Metadata } from "next";
import { PackageBuilder } from "@/components/PackageBuilder";
import { buildCatalog, presets, valuesArchetypes } from "@/lib/data";

export const metadata: Metadata = {
  title: "Build",
  description: "Put policies together and see what the package does to the ten-year deficit.",
};

export default function Build() {
  const rows = buildCatalog();
  // Illustrative reconstructions come last, as in the app.
  const ordered = [...rows.filter((r) => !r.illustrative), ...rows.filter((r) => r.illustrative)];
  const scored = presets().map((p) => p.id);
  return (
    <>
      <header>
        <span className="eyebrow">Build</span>
        <h1>Build a package</h1>
        <p className="sentence">
          Each policy carries a ten-year score, most of them published by CBO, JCT, Treasury or a research group;
          the source is named under each. The figure on each row is that published list price. Calculator&apos;s score
          opens Explore, which is this calculator&apos;s conventional estimate for the same policy. Ticking one that
          conflicts with another swaps them. A positive figure adds to the deficit; a negative one reduces it.
        </p>
      </header>
      <PackageBuilder rows={ordered} scored={scored} archetypes={valuesArchetypes()} />
    </>
  );
}
