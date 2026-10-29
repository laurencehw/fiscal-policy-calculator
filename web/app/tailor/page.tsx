import type { Metadata } from "next";
import { Suspense } from "react";
import { Tailor } from "@/components/Tailor";

export const metadata: Metadata = {
  title: "Tailor",
  description: "Score your own income or corporate tax rate change over ten years.",
};

export default function TailorPage() {
  return (
    <>
      <header>
        <span className="eyebrow">Tailor</span>
        <h1>Score your own rate change</h1>
        <p className="sentence">
          Raise or cut an income tax rate above a threshold you choose, or change the corporate rate, and the engine
          scores it over ten years. A positive figure adds to the deficit; a negative one reduces it.
        </p>
        <p className="note">
          The app also scores capital gains rates, spending changes and phase-ins; those come to this page later.
        </p>
      </header>
      <Suspense>
        <Tailor />
      </Suspense>
    </>
  );
}
