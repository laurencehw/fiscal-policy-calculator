// GET /api/v1/build: Build's list prices, from the latest snapshot.
import { json, notFound } from "@/lib/apiResponse";
import { snapshotFile, snapshotIndex } from "@/lib/data";
import { latestEntry, provenance } from "@/lib/research";
import { siteUrl } from "@/lib/site";

export const dynamic = "force-static";

export function GET() {
  const entry = latestEntry(snapshotIndex());
  if (!entry) return notFound("No snapshot has been exported yet.");
  const { data } = snapshotFile(entry);
  return json({
    ...provenance(data, siteUrl()),
    note: "A list price is the published or model score of one policy on its own. Build adds them; it does not score packages jointly.",
    build_catalog: data.build_catalog,
  });
}
