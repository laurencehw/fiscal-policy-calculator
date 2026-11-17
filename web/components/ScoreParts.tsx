// Pieces of a score page shared by Explore (static) and Tailor (live).
import { EstimateTag } from "@/components/EstimateTag";
import { money } from "@/lib/format";
import type { EstimateIdentity } from "@/lib/identity";
import { checkedSentence, hasOther, yearRows } from "@/lib/scoreparts";
import type { Credibility, ScoreResult } from "@/lib/types";

export function Checked({
  cred,
  point,
  window,
  published,
}: {
  cred: Credibility | null;
  point: number;
  window: string;
  published?: EstimateIdentity | null;
}) {
  if (!cred) return null;
  return (
    <section className="checked" aria-label="Checked against">
      <span className="tag">Checked against</span>
      {published ? <EstimateTag identity={published} /> : null}
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
  const rows = yearRows(c, d);
  const other = hasOther(rows);
  return (
    <div className="tablewrap">
      <table className="sheet">
        <thead>
          <tr>
            <th>Fiscal year</th>
            <th>Revenue, static</th>
            <th>Behavioural response</th>
            {other ? <th>Outlays and other</th> : null}
            <th>Deficit, conventional</th>
            <th>Macro feedback, deficit</th>
            <th>Debt service</th>
            <th>Deficit, dynamic</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.year}>
              <td>{row.year}</td>
              <td>{money(row.revenue)}</td>
              <td>{money(row.behavioural)}</td>
              {other ? <td>{money(row.other)}</td> : null}
              <td>{money(row.conventional)}</td>
              <td>{money(row.macro)}</td>
              <td>{row.debtService === null ? "" : money(row.debtService)}</td>
              <td>{row.dynamic === null ? "" : money(row.dynamic)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="note">
        The first two columns are revenue: positive is more revenue. The rest are deficit: positive adds to it. The
        conventional deficit is minus the two revenue columns{other ? ", plus outlays and other" : ""}, and the dynamic
        deficit adds macro feedback and debt service to it.
      </p>
    </div>
  );
}
