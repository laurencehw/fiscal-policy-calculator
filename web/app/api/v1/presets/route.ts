// GET /api/v1/presets: every Explore preset's ten-year figures, from the latest snapshot.
import { json, notFound } from "@/lib/apiResponse";
import { snapshotFile, snapshotIndex } from "@/lib/data";
import { latestEntry, presetSummaries, provenance } from "@/lib/research";
import { siteUrl } from "@/lib/site";

export const dynamic = "force-static";

export function GET() {
  const entry = latestEntry(snapshotIndex());
  if (!entry) return notFound("No snapshot has been exported yet.");
  const { data } = snapshotFile(entry);
  const site = siteUrl();
  return json({ ...provenance(data, site), presets: presetSummaries(data, site) });
}
