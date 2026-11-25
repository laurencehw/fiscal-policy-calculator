import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ChartActions } from "@/components/ChartActions";
import { BaselineChart } from "@/components/BaselineChart";
import { HouseStrip } from "@/components/HouseStrip";
import { YearChart } from "@/components/YearChart";
import { baseline, buildCatalog, houseStrip, manifest, preset, presets, views } from "@/lib/data";
import { buildPriceNote } from "@/lib/explore";
import { ResultSections } from "@/components/ResultSections";
import { EstimateTag } from "@/components/EstimateTag";
import { Checked, YearTable } from "@/components/ScoreParts";
import { yearRows } from "@/lib/scoreparts";
import { direction, money, plainDescription, shortLabel } from "@/lib/format";
import { adjustable, tailorHref } from "@/lib/adjust";
import { againstPre2025Law, estimateIdentity, identityLine, type EstimateIdentity } from "@/lib/identity";
import { baselineEyebrow } from "@/lib/lawStatus";
import { LawStatusNote } from "@/components/LawStatus";
import { CurrentLawAnswer } from "@/components/CurrentLawAnswer";
import { currentLawFigure } from "@/lib/lawStatus";
import { citation, versionRef } from "@/lib/share";
import { CiteBlock } from "@/components/CiteBlock";
import { StaleLink } from "@/components/StaleLink";
import { siteUrl } from "@/lib/site";
import { pageMeta } from "@/lib/meta";
import { takeaway } from "@/lib/takeaway";

export const dynamicParams = false;

export function generateStaticParams() {
  return presets().map((info) => ({ id: info.id }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const file = preset(id);
  if (!file) return {};
  const c = file.conventional;
  const info = presets().find((row) => row.id === id);
  const lawNow = currentLawFigure(info?.status, (other) => preset(other)?.conventional.ten_year_deficit_impact ?? null);
  const against = info?.status?.pre_2025_law ? " against pre-2025 law" : "";
  const meta = pageMeta({
    title: shortLabel(c.policy_name),
    description: `${money(c.ten_year_deficit_impact)} over ${c.budget_window}${against}: ${direction(c.ten_year_deficit_impact)}. ${plainDescription(c.policy_description)}`.slice(0, 199),
    path: `/explore/${id}`,
  });
  // The share card's text is the page's own opening sentence, so a link preview
  // says what the page says first.
  const opener = takeaway({
    c,
    table: views(id)?.distribution.groupings.jct_dollar,
    status: info?.status,
    currentLaw: lawNow,
    isPublished: info?.cbo_published !== false,
  });
  // This page's own card (./opengraph-image.tsx). Named here because a page's
  // explicit images would otherwise replace the file-based one.
  const card = { url: `/explore/${id}/opengraph-image`, width: 1200, height: 630, alt: `${shortLabel(c.policy_name)}: ten-year deficit effect` };
  return {
    ...meta,
    openGraph: { ...meta.openGraph, description: opener, images: [card] },
    twitter: { ...meta.twitter, description: opener, images: [card.url] },
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
  const v = views(id);
  const strip = houseStrip(id);
  const info = presets().find((row) => row.id === id);
  const scoresDate = versionRef(manifest().scores_date, manifest().scores_fingerprint);
  const status = info?.status ?? null;
  // A score that answers the pre-2025 question never carries the current baseline's name.
  const lawAware = (identity: EstimateIdentity) => (status?.pre_2025_law ? againstPre2025Law(identity) : identity);
  const modelIdentity = lawAware(estimateIdentity(c, "model"));
  const dynamicIdentity = lawAware(estimateIdentity(d, "model-dynamic"));
  const cite = citation({ title: name, identity: modelIdentity, path: `/explore/${id}`, scoresDate, site: siteUrl() });
  const lawNow = currentLawFigure(status, (other) => preset(other)?.conventional.ten_year_deficit_impact ?? null);
  const sameAs = status?.current_law?.same_as ?? null;
  const sameAsName = sameAs ? shortLabel(preset(sameAs)?.conventional.policy_name ?? sameAs) : null;
  const packageNote = buildPriceNote(
    buildCatalog().find((row) => row.build_id === id),
    headline,
    money,
  );
  const opener = takeaway({ c, table: v?.distribution.groupings.jct_dollar, status, currentLaw: lawNow, isPublished: info?.cbo_published !== false });
  const published =
    info?.cbo_published && info.cbo_source ? estimateIdentity({ ...c, cbo_source: info.cbo_source }, "published") : null;
  return (
    <div className="work">
      <header>
        <span className="eyebrow">{baselineEyebrow(c.budget_window, c.baseline_vintage, status)}</span>
        <h1>{name}</h1>
        <p className="takeaway">{opener}</p>
        {status ? <LawStatusNote status={status} /> : null}
        <p className="sentence">{plainDescription(c.policy_description)}</p>
        <StaleLink scoresDate={scoresDate} />
      </header>

      {status ? <CurrentLawAnswer status={status} figure={lawNow} vintage={c.baseline_vintage} sameAsName={sameAsName} /> : null}

      <div className="headline">
        <div className="stage">
          <span className="q">{status?.pre_2025_law ? "Against pre-2025 law: ten-year deficit effect, conventional" : "Ten-year deficit effect, conventional"}</span>
          <span className={`v ${headline > 0 ? "adds" : "reduces"}`}>{money(headline)}</span>
          <EstimateTag identity={modelIdentity} />
          <span className="q">{direction(headline)}</span>
        </div>
        <div className="stage">
          <span className="q">With demand feedback and debt service (supply side for corporate rates only)</span>
          <span className="v">{dyn === null ? "Not available" : money(dyn)}</span>
          <EstimateTag identity={dynamicIdentity} />
          <span className="q">{d.dynamic_model ?? d.error_message ?? ""}</span>
        </div>
      </div>

      <nav className="actions" aria-label="Proposal">
        <a href={`/build?add=${id}`}>Add to package</a>
        <a href={`/compare?ids=${id}`}>Compare</a>
        {adjustable(id) ? <a href={tailorHref(id) ?? "/tailor"}>Adjust in Tailor</a> : null}
        <a href="#exports">Share</a>
      </nav>
      {packageNote ? <p className="note">{packageNote}</p> : null}

      <Checked cred={c.credibility} point={headline} window={c.budget_window} published={published} />

      <BaselineChart
        years={baseline().years}
        effects={c.year_by_year.map((row) => ({ year: row.year, value: row.final_effect }))}
        headline={headline}
      />

      {strip ? <HouseStrip strip={strip} /> : null}

      <section className="chart">
        <div className="head">
          <h2>Year by year</h2>
          <EstimateTag identity={modelIdentity} />
        </div>
        <YearChart
          plotId="year-chart"
          rows={c.year_by_year.map((row) => ({ year: row.year, value: row.final_effect }))}
          label={`Annual deficit effect of ${name}, ${c.budget_window}`}
        />
        <YearTable c={c} d={d} />
        <p className="foot" id="exports">
          <a href={`/explore/${id}/csv`} download>
            Download CSV
          </a>
          <ChartActions
            chartId="year-chart"
            title={name}
            identity={identityLine(modelIdentity)}
            site={`Fiscal Policy Calculator, ${siteUrl().replace(/^https?:\/\//, "")}/explore/${id}`}
            scoresDate={scoresDate}
          />
        </p>
      </section>

      {v ? (
        <ResultSections
          views={v}
          conventional={modelIdentity}
          dynamic={dynamicIdentity}
          firstYear={yearRows(c, d)[0]}
        />
      ) : null}

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

      <CiteBlock cite={cite} />
    </div>
  );
}
