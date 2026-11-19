// GET /api/v1/snapshots: every frozen snapshot, oldest first.
import { json } from "@/lib/apiResponse";
import { snapshotIndex } from "@/lib/data";
import { API_BASE } from "@/lib/research";
import { siteUrl } from "@/lib/site";

export const dynamic = "force-static";

export function GET() {
  const index = snapshotIndex();
  const base = `${siteUrl()}${API_BASE}/snapshots`;
  return json({
    note: index.note,
    snapshots: index.snapshots.map((entry) => ({ ...entry, url: `${base}/${entry.id}` })),
  });
}
