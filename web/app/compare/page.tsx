import type { Metadata } from "next";
import Link from "next/link";
import { CompareSearch } from "@/components/CompareSearch";
import { EstimateTag } from "@/components/EstimateTag";
import { YearChart } from "@/components/YearChart";
import { preset, presets } from "@/lib/data";
import {
  differenceNote,
  differenceYears,
  refusedSentence,
  selectIds,
  sharedDomain,
  unknownSentence,
} from "@/lib/compare";
import { money, shortLabel } from "@/lib/format";
import { estimateIdentity } from "@/lib/identity";

export const metadata: Metadata = {
  title: "Compare",
  description: "Set two or three proposals beside each other on one scale.",
};

export default async function ComparePage({ searchParams }: { searchParams: Promise<{ ids?: string }> }) {
  const { ids: raw } = await searchParams;
  const catalog = presets().map((info) => ({ id: info.id, name: shortLabel(info.name) }));
  const picked = selectIds(raw, new Set(catalog.map((row) => row.id)));
  const items = picked.ids.flatMap((id) => {
    const file = preset(id);
    const info = presets().find((row) => row.id === id);
    if (!file || !info) return [];
    const conventional = file.conventional;
    return [
      {
        id,
        name: shortLabel(conventional.policy_name),
        window: conventional.budget_window,
        baseline: `CBO ${conventional.baseline_vintage}`,
        conventional: conventional.ten_year_deficit_impact,
        years: conventional.year_by_year.map((row) => ({ year: row.year, value: row.final_effect })),
        publishedValue: info.cbo_published ? info.cbo_score : null,
        published:
          info.cbo_published && info.cbo_source
            ? estimateIdentity({ ...conventional, cbo_source: info.cbo_source }, "published")
            : null,
        model: estimateIdentity(conventional, "model"),
      },
    ];
  });
  const note = differenceNote(items);
  const diff = note.draw && items.length === 2 ? differenceYears(items[0].years, items[1].years) : null;
  const domainValues = items.flatMap((item) => item.years.map((row) => row.value));

  return (
    <div className="work">
      <header>
        <span className="eyebrow">Compare</span>
        <h1>Set proposals side by side</h1>
        <p className="sentence">
          Up to three proposals, each with its own ten-year figure. I do not add them together.
        </p>
      </header>
      <CompareSearch catalog={catalog} selected={picked.ids} />
      {picked.unknown.length ? <p className="note">{unknownSentence(picked.unknown)}</p> : null}
      {picked.refused.length ? <p className="note">{refusedSentence(picked.refused)}</p> : null}
      {items.length === 0 ? <p className="note">Add a proposal to see it here.</p> : null}
      <div className="comparegrid">
        {items.map((item) => (
          <article key={item.id} className="comparecard">
            <h2>
              <Link href={`/explore/${item.id}`}>{item.name}</Link>
            </h2>
            <p className={`v ${item.conventional > 0 ? "adds" : "reduces"}`}>{money(item.conventional)}</p>
            <EstimateTag identity={item.model} />
            {item.published && item.publishedValue !== null ? (
              <p className="note">
                Published {money(item.publishedValue)} <EstimateTag identity={item.published} short />
              </p>
            ) : (
              <p className="note">No published score for this proposal.</p>
            )}
            <YearChart
              rows={item.years}
              domainValues={domainValues}
              height={180}
              label={`Annual deficit effect of ${item.name}, ${item.window}`}
            />
          </article>
        ))}
      </div>
      {diff ? (
        <section className="chart difference">
          <div className="head">
            <h2>Difference</h2>
            <span className="tag">
              {items[0].name} minus {items[1].name}
            </span>
          </div>
          <YearChart rows={diff} height={180} label={`Difference, ${items[0].name} minus ${items[1].name}`} />
        </section>
      ) : note.text ? (
        <p className="note">{note.text}</p>
      ) : null}
    </div>
  );
}
