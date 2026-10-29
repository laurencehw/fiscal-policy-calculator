import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { YearChart } from "@/components/YearChart";
import { preset, presets } from "@/lib/data";
import { cleanLabel, direction, money, pct, shortLabel } from "@/lib/format";
import { siteUrl } from "@/lib/site";
import type { Credibility, ScoreResult } from "@/lib/types";

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

function Checked({ cred }: { cred: Credibility | null }) {
  if (!cred) return null;
  return (
    <section className="checked" aria-label="Checked against">
      <span className="tag">Checked against</span>
      {cred.own_row_official_billions === null ? (
        <p>No published score for this exact policy is on file.</p>
      ) : (
        <p>
          Published score {money(cred.own_row_official_billions)}
          {cred.own_row_abs_pct_error === null ? "" : `; this estimate is ${pct(cred.own_row_abs_pct_error)} away`}
          {cred.own_row_tier_label ? ` (${cred.own_row_tier_label.toLowerCase()})` : ""}. {cred.own_row_caption}
        </p>
      )}
      {cred.uncertainty_low !== null && cred.uncertainty_high !== null ? (
        <p>
          Typical error for this kind of policy: {money(cred.uncertainty_low)} to {money(cred.uncertainty_high)}
          {cred.class_label ? `, from ${cred.n_tier1_rows} out-of-sample ${cred.class_label} cases` : ""}.
        </p>
      ) : null}
      <p className="note">{cred.caption}</p>
    </section>
  );
}

function Table({ c, d }: { c: ScoreResult; d: ScoreResult }) {
  return (
    <div className="tablewrap">
      <table className="sheet">
        <thead>
          <tr>
            <th>Fiscal year</th>
            <th>Revenue</th>
            <th>Deficit, conventional</th>
            <th>Macro feedback</th>
            <th>Debt service</th>
            <th>Deficit, dynamic</th>
          </tr>
        </thead>
        <tbody>
          {c.year_by_year.map((row, i) => {
            const dyn = d.year_by_year[i];
            return (
              <tr key={row.year}>
                <td>{row.year}</td>
                <td>{money(row.revenue_effect)}</td>
                <td>{money(row.final_effect)}</td>
                <td>{money(dyn?.dynamic_feedback ?? 0)}</td>
                <td>{dyn?.debt_service == null ? "" : money(dyn.debt_service)}</td>
                <td>{dyn?.dynamic_effect == null ? "" : money(dyn.dynamic_effect)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
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
        <Table c={c} d={d} />
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
