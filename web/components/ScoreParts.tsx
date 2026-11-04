// Pieces of a score page shared by Explore (static) and Tailor (live).
import { money } from "@/lib/format";
import { checkedSentence, yearRows } from "@/lib/scoreparts";
import type { Credibility, ScoreResult } from "@/lib/types";

export function Checked({ cred, point, window }: { cred: Credibility | null; point: number; window: string }) {
  if (!cred) return null;
  return (
    <section className="checked" aria-label="Checked against">
      <span className="tag">Checked against</span>
      <p>
        {checkedSentence(cred, point, window)}
        {cred.own_row_official_billions === null || !cred.own_row_caption ? "" : ` ${cred.own_row_caption}`}
      </p>
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

/**
 * One row per fiscal year: the conventional path from ``c``, the dynamic columns from ``d``.
 * Every column after Revenue is in the deficit convention, so conventional + macro + debt service = dynamic.
 */
export function YearTable({ c, d }: { c: ScoreResult; d: ScoreResult }) {
  return (
    <div className="tablewrap">
      <table className="sheet">
        <thead>
          <tr>
            <th>Fiscal year</th>
            <th>Revenue</th>
            <th>Deficit, conventional</th>
            <th>Macro feedback, deficit</th>
            <th>Debt service</th>
            <th>Deficit, dynamic</th>
          </tr>
        </thead>
        <tbody>
          {yearRows(c, d).map((row) => (
            <tr key={row.year}>
              <td>{row.year}</td>
              <td>{money(row.revenue)}</td>
              <td>{money(row.conventional)}</td>
              <td>{money(row.macro)}</td>
              <td>{row.debtService === null ? "" : money(row.debtService)}</td>
              <td>{row.dynamic === null ? "" : money(row.dynamic)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
