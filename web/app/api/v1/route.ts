// GET /api/v1: what the read-only data API offers. Documented at /data.
import { json } from "@/lib/apiResponse";
import { snapshotIndex } from "@/lib/data";
import { apiDirectory } from "@/lib/research";
import { siteUrl } from "@/lib/site";

export const dynamic = "force-static";

export function GET() {
  return json(apiDirectory(snapshotIndex(), siteUrl()));
}
