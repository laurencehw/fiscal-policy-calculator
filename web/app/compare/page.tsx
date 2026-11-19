import type { Metadata } from "next";
import { CompareView } from "@/components/CompareView";
import { pageMeta } from "@/lib/meta";

export const metadata: Metadata = pageMeta({
  title: "Compare",
  description: "Up to three proposals side by side: ten-year deficit effects, the year-by-year path on one axis, and the published scores.",
  path: "/compare",
});

// Pre-rendered. A list of proposals (?ids=) is rewritten to /compare/<ids> in next.config.ts.
export default function ComparePage() {
  return <CompareView ids={undefined} />;
}
