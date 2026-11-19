// GET /api/v1/snapshots/{ref}: one frozen snapshot, byte for byte as committed.
// ref is a snapshot id, a scores date (that day's last snapshot) or "latest".
import { jsonText, notFound } from "@/lib/apiResponse";
import { snapshotFile, snapshotIndex } from "@/lib/data";
import { resolveSnapshot, snapshotRefs } from "@/lib/research";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  return snapshotRefs(snapshotIndex()).map((ref) => ({ ref }));
}

export async function GET(_request: Request, { params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params;
  const entry = resolveSnapshot(snapshotIndex(), ref);
  if (!entry) return notFound(`No snapshot for ${ref}.`);
  // Only a full id names one file forever; a date or "latest" can point somewhere newer later.
  return jsonText(snapshotFile(entry).text, { immutable: ref === entry.id });
}
