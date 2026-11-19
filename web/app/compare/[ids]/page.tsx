import type { Metadata } from "next";
import { CompareView } from "@/components/CompareView";
import { DEFAULT_PAIR } from "@/lib/compare";
import { presets } from "@/lib/data";
import { pageMeta } from "@/lib/meta";

// "/compare?ids=<a,b,c>" lands here through a rewrite (next.config.ts), so the
// address bar keeps the query-string URL every link and share uses. The lists a
// visitor is most likely to open are built ahead: each proposal on its own (the
// Explore page's Compare link) and the default pair. Any other list is rendered
// on first request and then cached until the next deploy.
export const metadata: Metadata = pageMeta({
  title: "Compare",
  description: "Up to three proposals side by side: ten-year deficit effects, the year-by-year path on one axis, and the published scores.",
  path: "/compare",
});

export function generateStaticParams() {
  return [...presets().map((info) => ({ ids: info.id })), { ids: DEFAULT_PAIR.join(",") }];
}

export default async function CompareList({ params }: { params: Promise<{ ids: string }> }) {
  const { ids } = await params;
  return <CompareView ids={decodeURIComponent(ids)} />;
}
