import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { YearChart } from "@/components/YearChart";
import { preset, presets } from "@/lib/data";
import { Checked, YearTable } from "@/components/ScoreParts";
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
  const d = file.dynamic;
  const name = shortLabel(c.policy_name);
  const headline = c.ten_year_deficit_impact;
  const dyn = d.dynamic_adjusted_impact;
  return (
    <>
      <header>
        <span className="eyebrow">
          {c.budget_window} · CBO {c.baseline_vintage} baseline
        </span>
        <h1>{name}</h1>
        <p className="sentence">{cleanLabel(c.policy_description)}</p>
      </header>

      <div className="headline">
        <div className="stage">
          <span className="q">Ten-year deficit effect, conventional</span>
          <span className={`v ${headline > 0 ? "adds" : "reduces"}`}>{money(headline)}</span>
          <span className="q">{direction(headline)}</span>
        </div>
        <div className="stage">
          <span className="q">With macroeconomic feedback and debt service</span>
          <span className="v">{dyn === null ? "Not available" : money(dyn)}</span>
          <span className="q">{d.dynamic_model ?? d.error_message ?? ""}</span>
        </div>
      </div>

      <Checked cred={c.credibility} />

      <section className="chart">
        <div className="head">
          <h2>Year by year</h2>
          <span className="tag">billions, conventional</span>
        </div>
        <YearChart
          rows={c.year_by_year.map((row) => ({ year: row.year, value: row.final_effect }))}
          label={`Annual deficit effect of ${name}, ${c.budget_window}`}
        />
        <YearTable c={c} d={d} />
        <p className="foot">
          <a href={`/explore/${id}/csv`} download>
            Download CSV
          </a>
        </p>
      </section>

      {c.credibility?.limitations.length ? (
        <details className="latest">
          <summary>Limitations</summary>
          <ul className="marked">
            {c.credibility.limitations.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </details>
      ) : null}

      <p className="cite">
        <span className="tag">Cite as</span>
        <span>
          Wilse-Samson, Laurence. &ldquo;{name}.&rdquo; Fiscal Policy Calculator, CBO {c.baseline_vintage} baseline,{" "}
          {c.budget_window}. {siteUrl()}/explore/{id}
        </span>
      </p>
    </>
  );
}
