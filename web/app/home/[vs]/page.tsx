import type { Metadata } from "next";
import { HomeView } from "@/components/HomeView";
import { homeCandidates, homePair } from "@/lib/home";

// "/?vs=<id>" lands here through a rewrite (next.config.ts), so the address bar
// keeps the old URL. Every candidate is built ahead; anything else falls back to
// the default pair, as homePair always did, and is cached on first request.
export const metadata: Metadata = { alternates: { canonical: "/" } };

export function generateStaticParams() {
  return homeCandidates().map((c) => ({ vs: c.id }));
}

export default async function HomePair({ params }: { params: Promise<{ vs: string }> }) {
  const { vs } = await params;
  return <HomeView pair={homePair(decodeURIComponent(vs))} />;
}
