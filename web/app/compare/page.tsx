import type { Metadata } from "next";
import Link from "next/link";
import { Compare, type CompareCard } from "@/components/Compare";
import { CompareSearch, type CompareOption } from "@/components/CompareSearch";
import { preset, presets, presetsByArea } from "@/lib/data";
import { DEFAULT_PAIR, MAX_COMPARE, compareHref, droppedSentences, parseIds } from "@/lib/compare";
import { shortLabel } from "@/lib/format";
import { estimateIdentity } from "@/lib/identity";

export const metadata: Metadata = {
  title: "Compare",
  description: "Up to three proposals side by side: ten-year deficit effects, the year-by-year path on one axis, and the published scores.",
  alternates: { canonical: "/compare" },
};

export default async function ComparePage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  const index = presets();
  const known = new Set(index.map((info) => info.id));
  const parsed = parseIds(params.ids, known);
  const options: CompareOption[] = presetsByArea().flatMap((group) =>
    group.presets.map((info) => ({ id: info.id, name: shortLabel(info.name), area: group.area })),
  );
  const cards: CompareCard[] = parsed.ids.flatMap((id) => {
    const file = preset(id);
    if (!file) return [];
    const c = file.conventional;
    const info = index.find((row) => row.id === id);
    const published =
      info && info.cbo_published && info.cbo_score !== null && info.cbo_source
        ? {
            value: info.cbo_score,
            identity: estimateIdentity({ ...c, cbo_source: info.cbo_source }, "published"),
            date: info.cbo_date,
          }
        : null;
    return [
      {
        item: {
          id,
          name: shortLabel(c.policy_name),
          window: c.budget_window,
          baseline: c.baseline_vintage,
          tenYear: c.ten_year_deficit_impact,
          years: c.year_by_year.map((row) => ({ year: row.year, value: row.final_effect })),
        },
        calculator: estimateIdentity(c, "model"),
        published,
      },
    ];
  });
  const dropped = droppedSentences(parsed);
  const nameOf = (id: string) => options.find((option) => option.id === id)?.name ?? id;
  return (
    <div className="work">
      <header>
        <span className="eyebrow">Compare</span>
        <h1>Compare proposals</h1>
        <p className="sentence">
          Up to {MAX_COMPARE} proposals side by side. Every year-by-year chart uses the same axis, so bars of equal
          height are equal dollars. I never add the figures up: each is scored on its own.
        </p>
      </header>

      {dropped.length ? (
        <div className="note dropped" role="status">
          {dropped.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
      ) : null}

      <CompareSearch options={options} ids={parsed.ids} />

      {cards.length ? (
        <Compare cards={cards} />
      ) : (
        <p className="note">
          Pick a proposal above, or start from{" "}
          <Link href={compareHref([...DEFAULT_PAIR])}>
            {nameOf(DEFAULT_PAIR[0])} beside {nameOf(DEFAULT_PAIR[1])}
          </Link>
          , two figures read off the out-of-sample tier.
        </p>
      )}
    </div>
  );
}
