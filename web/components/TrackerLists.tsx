"use client";

import { useState } from "react";
import { money } from "@/lib/format";
import { PAGE_SIZE, billMoney, filterBills, showsAutoFigure } from "@/lib/tracker";
import type { TrackerRow } from "@/lib/types";

const STATUS: Record<string, string> = {
  introduced: "Introduced",
  committee: "In committee",
  passed_house: "Passed House",
  passed_senate: "Passed Senate",
  enacted: "Enacted",
};

const BILL_TYPE: Record<string, string> = {
  hr: "H.R.",
  s: "S.",
  hres: "H.Res.",
  sres: "S.Res.",
  hjres: "H.J.Res.",
  sjres: "S.J.Res.",
  hconres: "H.Con.Res.",
  sconres: "S.Con.Res.",
};

function billName(row: TrackerRow): string {
  return `${BILL_TYPE[row.type] ?? row.type.toUpperCase()} ${row.number}`;
}

/**
 * The calculator's reading beside a CBO figure: the number only when the model was reasonably sure.
 * "Confidence" here is the language model's confidence in its mapping of the text to provisions;
 * it says nothing about how reliable the dollar figure is, so the label says "mapping".
 */
function reading(row: TrackerRow): string {
  if (row.auto_ten_year_billions === null) return "";
  if (showsAutoFigure(row)) {
    return `${billMoney(row.auto_ten_year_billions, money)} (experimental, ${row.auto_confidence} mapping confidence)`;
  }
  if (row.auto_withheld?.length) return "withheld: failed a plausibility check";
  return "low mapping confidence";
}

/** The automated figure, or why it is not shown. */
function autoFigure(row: TrackerRow): string {
  if (row.auto_withheld?.length) return "Withheld";
  if (row.auto_ten_year_billions === 0) return "Nothing it could score";
  return billMoney(row.auto_ten_year_billions!, money);
}

function BillTable({ rows, figure }: { rows: TrackerRow[]; figure: "cbo" | "auto" }) {
  const [limit, setLimit] = useState(PAGE_SIZE);
  if (rows.length === 0) return <p className="note">No bills match.</p>;
  const figureLabel = figure === "cbo" ? "CBO, 10 years" : "Calculator, 10 years";
  return (
    <>
      <div className="tablescroll">
        <table className="sheet bills">
          <thead>
            <tr>
              <th scope="col">Bill</th>
              <th scope="col">Status</th>
              <th scope="col">{figureLabel}</th>
              {figure === "cbo" ? <th scope="col">Calculator</th> : <th scope="col">Mapping confidence</th>}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, limit).map((row) => {
              const value = figure === "cbo" ? row.cbo_ten_year_billions! : row.auto_ten_year_billions!;
              const withheld = figure === "auto" && (row.auto_withheld?.length ?? 0) > 0;
              const shown = withheld ? 0 : value;
              return (
                <tr key={row.id}>
                  <td className="billtitle">
                    {row.url ? <a href={row.url}>{billName(row)}</a> : billName(row)} <span>{row.title}</span>
                  </td>
                  <td data-label="Status">{STATUS[row.status] ?? row.status}</td>
                  <td data-label={figureLabel} className={shown > 0 ? "adds" : shown < 0 ? "reduces" : undefined}>
                    {figure === "cbo" ? billMoney(value, money) : autoFigure(row)}
                  </td>
                  {figure === "cbo" ? (
                    <td data-label="Calculator">{reading(row)}</td>
                  ) : (
                    <td data-label="Mapping confidence">
                      {row.auto_confidence ?? "none"}
                      {withheld ? <span className="note"> ({row.auto_withheld!.join("; ")})</span> : null}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {rows.length > limit ? (
        <div className="more">
          <span className="note">
            Showing {limit} of {rows.length.toLocaleString("en-US")}.
          </span>
          <button type="button" onClick={() => setLimit(limit + PAGE_SIZE * 2)}>
            Show more
          </button>
          <button type="button" onClick={() => setLimit(rows.length)}>
            Show all
          </button>
        </div>
      ) : null}
    </>
  );
}

/** The tracker's three lists under one filter: words or a bill number, and a status. */
export function TrackerLists({ cbo, auto, autoLow }: { cbo: TrackerRow[]; auto: TrackerRow[]; autoLow: TrackerRow[] }) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const pick = (rows: TrackerRow[]) => filterBills(rows, query, status);
  const shown = { cbo: pick(cbo), auto: pick(auto), autoLow: pick(autoLow) };
  const filtering = query.trim() !== "" || status !== "";
  return (
    <>
      <div className="exploretools trackertools">
        <label className="search">
          <span className="sr-only">Filter bills</span>
          <input
            type="search"
            placeholder="Bill number or words in the title, e.g. H.R. 1, veterans"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <label>
          <span className="sr-only">Status</span>
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Any status</option>
            {Object.entries(STATUS).map(([key, name]) => (
              <option key={key} value={key}>
                {name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {filtering ? (
        <p className="note" aria-live="polite">
          {shown.cbo.length} scored by CBO and {shown.auto.length + shown.autoLow.length} with an experimental
          reading match.
        </p>
      ) : null}

      <section>
        <h2>Scored by CBO</h2>
        <p className="note">
          The Congressional Budget Office&apos;s cost estimate, with the calculator&apos;s own reading of the bill
          beside it where it has one. Largest first.
        </p>
        <BillTable key={`cbo-${query}-${status}`} rows={shown.cbo} figure="cbo" />
      </section>

      <section>
        <h2>The calculator&apos;s own readings (experimental)</h2>
        <p className="note">
          For bills without a CBO estimate, a language model maps the bill&apos;s summary to provisions the calculator
          can score, and the engine then scores them. These readings are a demonstration, not estimates: the model
          misses provisions it cannot map and misreads some it does, for example treating a per-vehicle credit as a
          yearly budget total, or a rule for one occupation as a tax rate on everyone. So they are hidden unless you
          open them. A reading is withheld, with the reason, when it fails a plausibility check (a rate change larger
          than any the calculator has been tested on, a sign that contradicts the text, a one-time sum spent every
          year, or a total above $500B). The confidence column is the language model&apos;s confidence in its reading
          of the text, not a measure of how close the figure is to what CBO would find.
        </p>
        <details open={filtering && shown.auto.length > 0 ? true : undefined}>
          <summary>
            Show {shown.auto.length} experimental reading{shown.auto.length === 1 ? "" : "s"} that passed the checks
          </summary>
          <BillTable key={`auto-${query}-${status}`} rows={shown.auto} figure="auto" />
        </details>
        <details open={filtering && shown.autoLow.length > 0 ? true : undefined}>
          <summary>{shown.autoLow.length} withheld or low-confidence readings</summary>
          <p className="note">
            The model was unsure what these bills do, a check withheld the figure, or nothing in the bill could be
            scored. I list them only so that the list is complete; they are not informative.
          </p>
          <BillTable key={`low-${query}-${status}`} rows={shown.autoLow} figure="auto" />
        </details>
      </section>
    </>
  );
}
