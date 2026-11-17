import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ExplorePreset } from "@/components/ExplorePreset";
import { baseline, houseStrip, lawCatalog, manifest, preset, presets, views } from "@/lib/data";
import { cleanLabel, direction, money, shortLabel } from "@/lib/format";
import { siteUrl } from "@/lib/site";

export const dynamicParams = false;

export function generateStaticParams() {
  return presets().map((info) => ({ id: info.id }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const file = preset(id);
  if (!file) return {};
  const c = file.conventional;
  return {
    title: shortLabel(c.policy_name),
    description: `${money(c.ten_year_deficit_impact)} over ${c.budget_window}: ${direction(c.ten_year_deficit_impact)}. ${cleanLabel(c.policy_description)}`.slice(0, 199),
    alternates: { canonical: `/explore/${id}` },
  };
}

export default async function PresetPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const file = preset(id);
  if (!file) notFound();
  const c = file.conventional;
  const info = presets().find((row) => row.id === id);
  if (!info) notFound();
  return (
    <ExplorePreset
      id={id}
      name={shortLabel(c.policy_name)}
      description={cleanLabel(c.policy_description)}
      file={file}
      status={info.policy_status ?? null}
      info={info}
      views={views(id)}
      strip={houseStrip(id)}
      years={baseline().years}
      scoresDate={manifest().scores_date ?? ""}
      site={siteUrl()}
      catalog={lawCatalog()}
    />
  );
}
