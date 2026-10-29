import type { Metadata } from "next";
import { Suspense } from "react";
import { Generations } from "@/components/Generations";

export const metadata: Metadata = {
  title: "Generations",
  description: "Change capital taxes or Social Security and see the long-run economy and who carries the burden, by age.",
  alternates: { canonical: "/generations" },
};

export default function GenerationsPage() {
  return (
    <>
      <header>
        <span className="eyebrow">Overlapping-generations model · long run</span>
        <h1>Who carries a reform across generations</h1>
        <p className="sentence">
          Change the tax on capital or the size of Social Security, and a model of households who work, save and retire over a lifetime
          finds the new long-run economy and how the burden falls on people of each age.
        </p>
        <p className="note warn">
          Model estimate with a wide uncertainty band. The results rest on long-run parameters (patience, how much people work,
          population growth) that are uncertain, so read them as direction and rough size, not as point estimates. This model is
          separate from the ten-year scores on Explore and Tailor.
        </p>
      </header>
      <Suspense>
        <Generations />
      </Suspense>
      <p className="note">
        A 55-period Auerbach-Kotlikoff model (ages 21 to 75) with a Cobb-Douglas economy, solved for each steady state and for the
        75-year path between them. Capital income tax covers corporate and individual taxes together.
      </p>
    </>
  );
}
