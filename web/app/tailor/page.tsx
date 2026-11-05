import type { Metadata } from "next";
import { Suspense } from "react";
import { Tailor } from "@/components/Tailor";
import { StaleLink } from "@/components/StaleLink";
import { manifest } from "@/lib/data";

export const metadata: Metadata = {
  title: "Tailor",
  description: "Score your own income or corporate tax rate change over ten years.",
};

export default function TailorPage() {
  const scoresDate = manifest().scores_date ?? "";
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
        <Tailor scoresDate={scoresDate} />
      </Suspense>
    </div>
  );
}
