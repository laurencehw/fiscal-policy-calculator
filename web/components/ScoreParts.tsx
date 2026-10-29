// Pieces of a score page shared by Explore (static) and Tailor (live).
import { money, pct } from "@/lib/format";
import type { Credibility, ScoreResult } from "@/lib/types";

export function Checked({ cred }: { cred: Credibility | null }) {
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

/** One row per fiscal year: the conventional path from ``c``, the dynamic columns from ``d``. */
export function YearTable({ c, d }: { c: ScoreResult; d: ScoreResult }) {
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
