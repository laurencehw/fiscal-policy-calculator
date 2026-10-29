import type { Metadata } from "next";
import { trackerGroups, trackerIndex } from "@/lib/data";
import { money } from "@/lib/format";
import type { TrackerRow } from "@/lib/types";

export const metadata: Metadata = {
  title: "Bill tracker",
  description: "Bills in Congress with a ten-year budget estimate, from CBO or from the calculator's reading of the text.",
};

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
    return `${money(row.auto_ten_year_billions)} (${row.auto_confidence} confidence)`;
  }
  return "low confidence";
}

function day(iso: string | null): string {
  return iso ? iso.slice(0, 10) : "";
}

function BillTable({ rows, figure }: { rows: TrackerRow[]; figure: "cbo" | "auto" }) {
  return (
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
          {rows.map((row) => {
            const value = figure === "cbo" ? row.cbo_ten_year_billions! : row.auto_ten_year_billions!;
            return (
              <tr key={row.id}>
                <td className="billtitle">
                  {row.url ? <a href={row.url}>{billName(row)}</a> : billName(row)} <span>{row.title}</span>
                </td>
                <td>{STATUS[row.status] ?? row.status}</td>
                <td className={value > 0 ? "adds" : value < 0 ? "reduces" : undefined}>{money(value)}</td>
                {figure === "cbo" ? (
                  <td>{reading(row)}</td>
                ) : (
                  <td>{row.auto_confidence ?? "none"}</td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function Tracker() {
  const index = trackerIndex();
  const { cbo, auto, autoLow } = trackerGroups(index);
  return (
    <>
      <header>
        <span className="eyebrow">Bill tracker</span>
        <h1>Bills with a budget estimate</h1>
        <p className="sentence">
          Of {index.bills.toLocaleString("en-US")} bills in the 119th Congress followed nightly,{" "}
          {(cbo.length + auto.length + autoLow.length).toLocaleString("en-US")} have a ten-year estimate. A
          positive figure adds to the deficit; a negative one reduces it. Updated {day(index.last_update)}.
        </p>
      </header>

      <section>
        <h2>Scored by CBO</h2>
        <p className="note">
          The Congressional Budget Office&apos;s cost estimate, with the calculator&apos;s own reading of the bill
          beside it where it has one.
        </p>
        <BillTable rows={cbo} figure="cbo" />
      </section>

      <section>
        <h2>Read by the calculator</h2>
        <p className="note">
          No CBO estimate yet. A language model maps the bill&apos;s text to provisions the calculator can score,
          then the engine scores them. This is a demonstration, not an estimate to cite: it misses provisions it
          cannot map and can misread the ones it does. Only medium- and high-confidence readings are listed here.
        </p>
        <BillTable rows={auto} figure="auto" />
        <details>
          <summary>{autoLow.length} low-confidence readings</summary>
          <p className="note">
            The model was unsure what these bills do. Some figures are far from any plausible cost; they are shown
            so the list is complete, not because they are informative.
          </p>
          <BillTable rows={autoLow} figure="auto" />
        </details>
      </section>
    </>
  );
}
