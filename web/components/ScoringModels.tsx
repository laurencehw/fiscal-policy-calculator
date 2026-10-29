// The same policy through every pilot scoring backend. Exploratory tier: shown for robustness, not as a validated range.
import { money } from "@/lib/format";
import type { ModelsView } from "@/lib/types";

export function ScoringModels({ view }: { view: ModelsView }) {
  return (
    <>
      <div className="tablewrap">
        <table className="sheet words">
          <thead>
            <tr>
              <th>Model</th>
              <th>Ten-year deficit effect</th>
              <th>Method</th>
            </tr>
          </thead>
          <tbody>
            {view.results.map((r) => (
              <tr key={r.model}>
                <td>{r.model}</td>
                <td className="num">{money(r.ten_year_billions)}</td>
                <td>
                  {r.methodology}
                  {r.notes.length ? <span className="cite"> {r.notes.join(" ")}</span> : null}
                </td>
              </tr>
            ))}
            {view.skipped.map((s) => (
              <tr key={s.model}>
                <td>{s.model}</td>
                <td className="num">{s.kind === "not_representable" ? "Cannot score this" : "Did not run"}</td>
                <td>{s.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {[...view.blockers, ...view.warnings].map((line) => (
        <p className="note" key={line}>
          {line}
        </p>
      ))}
      <p className="note">
        CBO-Style is the model behind the headline above. The TPC-style microsimulation is a pilot: where the two disagree, the gap
        tells you how much the answer depends on method. It is not an official range.
      </p>
    </>
  );
}
