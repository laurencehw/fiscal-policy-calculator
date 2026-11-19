// GET /api/v1/validation: the validation tiers, from the latest snapshot.
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
    note: "Report the tiers separately. The out-of-sample tier is the test; calibrated rows agree with their targets by construction.",
    validation: data.validation,
  });
}
