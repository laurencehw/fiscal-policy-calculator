// GET /api/v1/presets/{id}: one preset in full, from the latest snapshot.
import { json, notFound } from "@/lib/apiResponse";
import { snapshotFile, snapshotIndex } from "@/lib/data";
import { latestEntry, provenance } from "@/lib/research";
import { siteUrl } from "@/lib/site";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  const entry = latestEntry(snapshotIndex());
  return entry ? snapshotFile(entry).data.presets.map((item) => ({ id: item.id })) : [];
}

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const entry = latestEntry(snapshotIndex());
  if (!entry) return notFound("No snapshot has been exported yet.");
  const { data } = snapshotFile(entry);
  const item = data.presets.find((row) => row.id === id);
  if (!item) return notFound(`No preset with id ${id}.`);
  const site = siteUrl();
  return json({ ...provenance(data, site), page_url: `${site}/explore/${id}?v=${data.scores_date}`, preset: item });
}
