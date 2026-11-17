"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { EstimateTag } from "@/components/EstimateTag";
import { LawLesson } from "@/components/LawLesson";
import { LawSwitch } from "@/components/LawSwitch";
import { PolicyStatusBadge } from "@/components/PolicyStatusNotice";
import { MAX_COMPARE, compareHref, toggleId } from "@/lib/compare";
import { arrange, byDirection, filterRows, scaleOf, viewFromQuery, type ExploreRow, type ExploreShow, type ExploreSort } from "@/lib/explore";
import { money } from "@/lib/format";
import { estimateIdentity, type EstimateIdentity } from "@/lib/identity";
import {
  DEFAULT_LAW,
  displayedPublished,
  displayedScore,
  lawInfo,
  presentPreset,
  withLaw,
  type LawCatalog,
  type LawId,
  type Presentation,
} from "@/lib/lawBaseline";

function Bar({ value, scale, published }: { value: number; scale: number; published?: boolean }) {
  const width = `${Math.max(1, (Math.abs(value) / scale) * 100)}%`;
  const tone = published ? "published" : value > 0 ? "adds" : "reduces";
  return (
    <span className="bartrack" aria-hidden="true">
      <span className={`bar ${tone}`} style={{ width }} />
    </span>
  );
}

type ShownRow = ExploreRow & { presentation: Presentation };

function writeLaw(law: LawId) {
  const url = new URL(window.location.href);
  if (law === DEFAULT_LAW) url.searchParams.delete("law");
  else url.searchParams.set("law", law);
  window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
}

function ScoreCell({
  value,
  scale,
  presentation,
  published,
}: {
  value: number | null;
  scale: number;
  presentation: Presentation;
  published?: boolean;
}) {
  if (value === null) {
    const blank = published && presentation.show_published ? "none" : "—";
    return (
      <span className="figcell">
        <span className="fig none" title={presentation.explanation ?? undefined}>
          {blank}
        </span>
      </span>
    );
  }
  const approx = !presentation.score_is_on_this_law;
  return (
    <span className="figcell">
      <span
        className={`fig ${published ? "published" : value > 0 ? "adds" : "reduces"}`}
        title={presentation.explanation ?? undefined}
      >
        <span className="sr-only">{published ? "Published: " : "Calculator: "}</span>
        {money(value)}
        {approx ? <span className="approx">approx.</span> : null}
      </span>
      {value === 0 ? null : <Bar value={value} scale={scale} published={published} />}
    </span>
  );
}

/** Explore's list: a filter box, a sort toggle, and one bar per figure on a shared scale. */
export function ExploreList({
  rows,
  calculator,
  published,
  catalog,
}: {
  rows: ExploreRow[];
  calculator: EstimateIdentity;
  published: EstimateIdentity;
  catalog: LawCatalog;
}) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<ExploreSort>("topic");
  const [picked, setPicked] = useState<string[]>([]);
  const [show, setShow] = useState<ExploreShow>("all");
  const [law, setLaw] = useState<LawId>(DEFAULT_LAW);
  // A link such as /explore?show=reduces&sort=size&law=pre2025 opens on that view.
  useEffect(() => {
    const view = viewFromQuery(window.location.search);
    setQuery(view.query);
    setSort(view.sort);
    setShow(view.show);
    setLaw(view.law);
  }, []);

  const onLaw = (next: LawId) => {
    setLaw(next);
    writeLaw(next);
  };

  const viewed = useMemo<ShownRow[]>(
    () =>
      rows.map((row) => {
        const presentation = presentPreset(catalog, row.id, law);
        return {
          ...row,
          conventional: displayedScore(row.conventional, presentation),
          published: displayedPublished(row.published, presentation),
          presentation,
        };
      }),
    [rows, catalog, law],
  );

  const scale = useMemo(() => scaleOf(viewed), [viewed]);
  const shown = filterRows(byDirection(viewed, show), query);
  const groups = arrange(shown, sort);
  const yardstick = lawInfo(catalog, law);
  const calculatorTag = estimateIdentity(
    { budget_window: calculator.window, credibility: null },
    "model",
    { baselineOverride: yardstick.phrase },
  );
  return (
    <div className="explore">
      <div className="exploretools">
        <LawSwitch catalog={catalog} value={law} onChange={onLaw} />
        <label className="search">
          <span className="sr-only">Filter proposals</span>
          <input
            type="search"
            placeholder="Filter, e.g. corporate, tariff, SALT"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <div className="seg" role="group" aria-label="Order">
          <button type="button" aria-pressed={sort === "topic"} onClick={() => setSort("topic")}>
            By topic
          </button>
          <button type="button" aria-pressed={sort === "size"} onClick={() => setSort("size")}>
            Largest first
          </button>
        </div>
        <div className="exploremeta">
          <p className="note" aria-live="polite">
            {shown.length === rows.length ? `${rows.length} proposals.` : `${shown.length} of ${rows.length} proposals.`}
            {show !== "all" ? ` Only those that ${show === "reduces" ? "reduce" : "add to"} the deficit. ` : null}
            {show !== "all" ? (
              <button type="button" className="linkish" onClick={() => setShow("all")}>
                Show all
              </button>
            ) : null}
            {shown.length === 0 ? " Nothing matches; try a shorter word." : null}
          </p>
          <LawLesson catalog={catalog} law={law} compact />
        </div>
        {picked.length ? (
          <p className="comparepick" aria-live="polite">
            <Link href={compareHref(picked)}>
              Compare {picked.length} {picked.length === 1 ? "proposal" : "proposals"}
            </Link>
            {picked.length >= MAX_COMPARE ? <span className="note"> (the most the page shows)</span> : null}
            <button type="button" onClick={() => setPicked([])}>
              Clear
            </button>
          </p>
        ) : null}
      </div>
      <ul className="presetlist explorelist">
        <li className="explorehead" aria-hidden="true">
          <span />
          <span className="figlabel">
            <EstimateTag identity={calculatorTag} short />
          </span>
          <span className="figlabel">
            <EstimateTag identity={published} short />
          </span>
        </li>
        {groups.flatMap((group) => [
          group.area ? (
            <li key={group.area} className="exploresection">
              <h2>{group.area}</h2>
            </li>
          ) : null,
          ...group.rows.map((row) => {
            const shownRow = row as ShownRow;
            return (
              <li key={shownRow.id}>
                <span className="rowname">
                  <input
                    type="checkbox"
                    aria-label={`Compare ${shownRow.name}`}
                    title="Compare"
                    checked={picked.includes(shownRow.id)}
                    disabled={!picked.includes(shownRow.id) && picked.length >= MAX_COMPARE}
                    onChange={() => setPicked((ids) => toggleId(ids, shownRow.id))}
                  />
                  <span className="rowlabel">
                    <Link href={withLaw(`/explore/${shownRow.id}`, law)}>{shownRow.name}</Link>
                    <PolicyStatusBadge status={shownRow.status} />
                  </span>
                </span>
                <ScoreCell value={shownRow.conventional} scale={scale} presentation={shownRow.presentation} />
                <ScoreCell
                  value={shownRow.published}
                  scale={scale}
                  presentation={shownRow.presentation}
                  published
                />
              </li>
            );
          }),
        ])}
      </ul>
    </div>
  );
}
