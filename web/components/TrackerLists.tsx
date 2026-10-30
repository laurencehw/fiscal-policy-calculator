"use client";

import { useState } from "react";
import { money } from "@/lib/format";
import { PAGE_SIZE, billMoney, filterBills } from "@/lib/tracker";
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

/** The calculator's reading beside a CBO figure: the number only when the model was reasonably sure. */
function reading(row: TrackerRow): string {
  if (row.auto_ten_year_billions === null) return "";
  if (row.auto_confidence === "high" || row.auto_confidence === "medium") {
    return `${billMoney(row.auto_ten_year_billions, money)} (${row.auto_confidence} confidence)`;
  }
  return "low confidence";
}

function BillTable({ rows, figure }: { rows: TrackerRow[]; figure: "cbo" | "auto" }) {
  const [limit, setLimit] = useState(PAGE_SIZE);
  if (rows.length === 0) return <p className="note">No bills match.</p>;
  return (
    <>
      <div className="tablescroll">
        <table className="sheet bills">
          <thead>
            <tr>
              <th scope="col">Bill</th>
              <th scope="col">Status</th>
              <th scope="col">{figure === "cbo" ? "CBO, 10 years" : "Calculator, 10 years"}</th>
              {figure === "cbo" ? <th scope="col">Calculator</th> : <th scope="col">Confidence</th>}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, limit).map((row) => {
              const value = figure === "cbo" ? row.cbo_ten_year_billions! : row.auto_ten_year_billions!;
              return (
                <tr key={row.id}>
                  <td className="billtitle">
                    {row.url ? <a href={row.url}>{billName(row)}</a> : billName(row)} <span>{row.title}</span>
                  </td>
                  <td>{STATUS[row.status] ?? row.status}</td>
                  <td className={value > 0 ? "adds" : value < 0 ? "reduces" : undefined}>{billMoney(value, money)}</td>
                  {figure === "cbo" ? <td>{reading(row)}</td> : <td>{row.auto_confidence ?? "none"}</td>}
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
          {shown.cbo.length} scored by CBO and {shown.auto.length + shown.autoLow.length} read by the calculator
          match.
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
        <h2>Read by the calculator</h2>
        <p className="note">
          No CBO estimate yet. A language model maps the bill&apos;s text to provisions the calculator can score,
          then the engine scores them. This is a demonstration, not an estimate to cite: it misses provisions it
          cannot map and can misread the ones it does. Only medium- and high-confidence readings are listed here.
        </p>
        <BillTable key={`auto-${query}-${status}`} rows={shown.auto} figure="auto" />
        <details open={filtering && shown.autoLow.length > 0 ? true : undefined}>
          <summary>{shown.autoLow.length} low-confidence readings</summary>
          <p className="note">
            The model was unsure what these bills do. Some figures are far from any plausible cost; they are shown
            so the list is complete, not because they are informative.
          </p>
          <BillTable key={`low-${query}-${status}`} rows={shown.autoLow} figure="auto" />
        </details>
      </section>
    </>
  );
}
