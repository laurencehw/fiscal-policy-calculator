import { HomeView } from "@/components/HomeView";
import { homePair } from "@/lib/home";

// Pre-rendered at build time. A swapped pair (/?vs=<id>) is rewritten to
// /home/<id> in next.config.ts, which is cached per pair.
export default function Home() {
  return <HomeView pair={homePair(undefined)} />;
}
