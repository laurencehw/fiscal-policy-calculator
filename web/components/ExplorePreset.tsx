"use client";

import { useEffect, useState } from "react";
import { ChartActions } from "@/components/ChartActions";
import { BaselineChart } from "@/components/BaselineChart";
import { HouseStrip } from "@/components/HouseStrip";
import { YearChart } from "@/components/YearChart";
import { ResultSections } from "@/components/ResultSections";
import { EstimateTag } from "@/components/EstimateTag";
import { Checked, YearTable } from "@/components/ScoreParts";
import { CiteBlock } from "@/components/CiteBlock";
import { LawLesson } from "@/components/LawLesson";
import { LawSwitch } from "@/components/LawSwitch";
import { PolicyStatusNotice } from "@/components/PolicyStatusNotice";
import { StaleLink } from "@/components/StaleLink";
import { adjustable, tailorHref } from "@/lib/adjust";
import type { BaselineYear } from "@/lib/baseline";
import { direction, money } from "@/lib/format";
import type { HouseStripData } from "@/lib/houses";
import { estimateIdentity, identityLine } from "@/lib/identity";
import {
  DEFAULT_LAW,
  displayedScore,
  lawFromQuery,
  lawInfo,
  presentPreset,
  withLaw,
  type LawCatalog,
  type LawId,
} from "@/lib/lawBaseline";
import { citation } from "@/lib/share";
import type { PolicyStatusInfo, PresetFile, PresetInfo, ResultViews } from "@/lib/types";

function writeLaw(id: string, law: LawId) {
  const url = new URL(window.location.href);
  url.pathname = `/explore/${id}`;
  if (law === DEFAULT_LAW) url.searchParams.delete("law");
  else url.searchParams.set("law", law);
  window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
}

function Headline({
  question,
  value,
  identity,
  note,
}: {
  question: string;
  value: number | null;
  identity: ReturnType<typeof estimateIdentity>;
  note: string;
}) {
  return (
    <div className="stage">
      <span className="q">{question}</span>
      <span className={`v ${value === null ? "" : value > 0 ? "adds" : "reduces"}`}>
        {value === null ? "Not yet computed" : money(value)}
      </span>
      <EstimateTag identity={identity} />
      <span className="q">{note}</span>
    </div>
  );
}

export function ExplorePreset({
  id,
  name,
  description,
  file,
  status,
  info,
  views,
  strip,
  years,
  scoresDate,
  site,
  catalog,
}: {
  id: string;
  name: string;
  description: string;
  file: PresetFile;
  status: PolicyStatusInfo | null;
  info: PresetInfo;
  views: ResultViews | null;
  strip: HouseStripData | null;
  years: BaselineYear[];
  scoresDate: string;
  site: string;
  catalog: LawCatalog;
}) {
  const [law, setLaw] = useState<LawId>(DEFAULT_LAW);
  useEffect(() => {
    setLaw(lawFromQuery(window.location.search));
  }, []);
  const onLaw = (next: LawId) => {
    setLaw(next);
    writeLaw(id, next);
  };

  const c = file.conventional;
  const d = file.dynamic;
  const stored = c.ten_year_deficit_impact;
  const storedDynamic = d.dynamic_adjusted_impact;
  const presentation = presentPreset(catalog, id, law);
  const yardstick = lawInfo(catalog, law);
  const shown = displayedScore(stored, presentation);
  const shownDynamic =
    presentation.display_score === 0 ? 0 : presentation.display_score === "stored" ? storedDynamic : null;
  const onCurrent = status?.on_current_baseline;
  const scored = { ...c, on_current_baseline: onCurrent };
  const scoredDynamic = { ...d, on_current_baseline: onCurrent };
  const modelIdentity = estimateIdentity(scored, "model", { baselineOverride: presentation.identity_baseline });
  const dynamicIdentity = estimateIdentity(scoredDynamic, "model-dynamic", {
    baselineOverride: presentation.identity_baseline,
  });
  const reconstructionIdentity = estimateIdentity(
    { ...c, on_current_baseline: false },
    "model",
    { baselineOverride: catalog.laws.find((row) => row.id === "pre2025")?.phrase },
  );
  const cite = citation({
    title: name,
    identity: modelIdentity,
    path: withLaw(`/explore/${id}`, law),
    scoresDate,
    site,
  });
  const published =
    info.cbo_published && info.cbo_source && presentation.show_published
      ? estimateIdentity({ ...c, cbo_source: info.cbo_source }, "published")
      : null;
  const showPath = presentation.kind === "reconstruction" || presentation.kind === "live";
  const showReconstruction =
    presentation.kind === "already_law" || presentation.kind === "remainder_unscored";

  return (
    <div className="work">
      <header>
        <span className="eyebrow">
          {c.budget_window} · {yardstick.phrase}
        </span>
        <h1>{name}</h1>
        <p className="sentence">{description}</p>
        <LawSwitch catalog={catalog} value={law} onChange={onLaw} />
        <StaleLink scoresDate={scoresDate} />
      </header>

      <div className="headline">
        <Headline
          question={`Ten-year deficit effect, conventional, vs ${yardstick.short_label.toLowerCase()}`}
          value={shown}
          identity={modelIdentity}
          note={shown === null ? "The remainder against this baseline is not yet scored." : direction(shown)}
        />
        <Headline
          question="With macroeconomic feedback and debt service"
          value={shownDynamic}
          identity={dynamicIdentity}
          note={d.dynamic_model ?? d.error_message ?? ""}
        />
      </div>

      <PolicyStatusNotice status={status} />
      {presentation.explanation ? (
        <p className="statusnotice" role="note">
          {presentation.explanation}
        </p>
      ) : null}
      <LawLesson catalog={catalog} law={law} />

      {showReconstruction ? (
        <div className="headline reconstruction">
          <Headline
            question="The same proposal vs pre-2025 law (the stored reconstruction)"
            value={stored}
            identity={reconstructionIdentity}
            note={direction(stored)}
          />
          <p className="note">
            <a href={withLaw(`/explore/${id}`, "pre2025")}>View this proposal against pre-2025 law</a>
            {law !== "extended" ? (
              <>
                {" · "}
                <a href={withLaw(`/explore/${id}`, "extended")}>or with temporary provisions extended</a>
              </>
            ) : null}
            .
          </p>
        </div>
      ) : null}

      <nav className="actions" aria-label="Proposal">
        <a href={`/build?add=${id}`}>Add to package</a>
        <a href={`/compare?ids=${id}`}>Compare</a>
        {adjustable(id) ? <a href={tailorHref(id) ?? "/tailor"}>Adjust in Tailor</a> : null}
        <a href="#exports">Share</a>
      </nav>

      {showPath && shown !== null ? (
        <Checked cred={c.credibility} point={shown} window={c.budget_window} published={published} />
      ) : null}

      {showPath ? (
        <BaselineChart
          years={years}
          effects={c.year_by_year.map((row) => ({ year: row.year, value: row.final_effect }))}
          headline={stored}
        />
      ) : (
        <p className="note">
          The year-by-year path and the chart on CBO&apos;s February 2026 deficit are the pre-2025-law
          reconstruction. They are not an incremental path against this yardstick; switch to pre-2025 law to
          see them as a score.
        </p>
      )}

      {showPath && strip ? <HouseStrip strip={strip} /> : null}

      {showPath ? (
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
              site={`Fiscal Policy Calculator, ${site.replace(/^https?:\/\//, "")}${withLaw(`/explore/${id}`, law)}`}
              scoresDate={scoresDate}
            />
          </p>
        </section>
      ) : (
        <p className="foot" id="exports">
          <a href={`/explore/${id}/csv`} download>
            Download CSV
          </a>
          {" "}(the pre-2025-law reconstruction)
        </p>
      )}

      {showPath && views ? (
        <ResultSections views={views} conventional={modelIdentity} dynamic={dynamicIdentity} />
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

      <CiteBlock text={cite.text} />
    </div>
  );
}
