import type { Metadata } from "next";
import { PresetList } from "@/components/PresetList";
import { manifest, presetsByArea } from "@/lib/data";

export const metadata: Metadata = {
  title: "Explore",
  description: "Every preset proposal, with its ten-year deficit effect.",
};

export default function Explore() {
  const m = manifest();
  return (
    <>
      <header>
        <span className="eyebrow">Explore</span>
        <h1>Proposals</h1>
        <p className="sentence">
          Ten-year conventional deficit effects, {m.budget_windows.join(", ")}. A positive figure adds to the
          deficit; a negative one reduces it.
        </p>
      </header>
      <div className="presetgroups">
        {presetsByArea().map((group) => (
          <section key={group.area} className="presetgroup">
            <h2>{group.area}</h2>
            <PresetList items={group.presets} />
          </section>
        ))}
      </div>
    </>
  );
}
