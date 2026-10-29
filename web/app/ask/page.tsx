import type { Metadata } from "next";
import { Suspense } from "react";
import { Ask } from "@/components/Ask";

export const metadata: Metadata = {
  title: "Ask",
  description: "Ask a question about the federal budget or a tax or spending policy. Answers use this calculator's scores and cite their sources.",
  alternates: { canonical: "/ask" },
};

export default function AskPage() {
  return (
    <>
      <header>
        <span className="eyebrow">Ask · answers by Claude, grounded in this calculator</span>
        <h1>Ask about the budget</h1>
        <p className="sentence">
          Ask about the deficit, a tax or spending proposal, or a score on this site. The assistant can run the calculator, read CBO&apos;s
          baseline and a set of curated sources, and search a short list of official sites, and it cites what it uses.
        </p>
        <p className="note">
          Answers come from an AI model and can be wrong; follow the citations before relying on one. The assistant&apos;s scores are the
          calculator&apos;s own estimates, not CBO&apos;s or JCT&apos;s. There is a daily limit per visitor and a daily budget for the whole site.
          Questions are sent to Anthropic to answer and are not stored by this site.
        </p>
      </header>
      <Suspense>
        <Ask />
      </Suspense>
    </>
  );
}
