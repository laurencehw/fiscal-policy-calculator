import { preset, presets, yearCsv } from "@/lib/data";

export const dynamic = "force-static";

export function generateStaticParams() {
  return presets().map((info) => ({ id: info.id }));
}

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const file = preset(id);
  if (!file) return new Response("Not found", { status: 404 });
  const onCurrent = presets().find((row) => row.id === id)?.policy_status?.on_current_baseline !== false;
  return new Response(yearCsv(file.conventional, file.dynamic, onCurrent), {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="${id}.csv"`,
    },
  });
}
