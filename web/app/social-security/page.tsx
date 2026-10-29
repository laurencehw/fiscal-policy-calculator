import type { Metadata } from "next";
import { SocialSecurityMenu } from "@/components/SocialSecurity";
import { socialSecurity } from "@/lib/data";

export const metadata: Metadata = {
  title: "Social Security",
  description: "Pick reform options from SSA's actuaries and see how far they go toward keeping Social Security solvent for 75 years.",
};

const CRFB_REFORMER_URL = "https://www.crfb.org/socialsecurityreformer/";
const OCACT_INDEX_URL = "https://www.ssa.gov/oact/solvency/provisions/index.html";
const TRUSTEES_URL = "https://www.ssa.gov/oact/tr/2026/";

export default function SocialSecurity() {
  const data = socialSecurity();
  const t = data.trustees;
  return (
    <>
      <header>
        <span className="eyebrow">Social Security</span>
        <h1>Fix the trust fund</h1>
        <p className="sentence">
          Pick reform options and see how far they go toward keeping Social Security solvent for the next 75 years.
        </p>
        <p className="note">
          Each option&apos;s effect is the estimate of SSA&apos;s Office of the Chief Actuary on the 2026 Trustees Report
          baseline, transcribed, not a model estimate. The calculator only runs the trust fund ledger. Options are
          added without interactions, as in CRFB&apos;s Reformer, so a plan&apos;s total is a rough guide, not a formal score.
        </p>
      </header>

      {/* The parity checks are for the tests; the browser does not need them. */}
      <SocialSecurityMenu data={{ ...data, checks: [] }} />

      <p className="note">
        This page models the combined OASDI funds (retirement plus disability), which the Trustees project to run out
        in {t.oasdi_depletion_year} with {t.oasdi_payable_pct}% of scheduled benefits payable. The retirement fund alone
        (OASI) runs out sooner, in {t.oasi_depletion}, with {t.oasi_payable_pct}% payable: a {100 - t.oasi_payable_pct}% cut.
        That is the headline CRFB uses, so the two tools&apos; current-law dates differ by definition, not by disagreement.
      </p>

      <section>
        <h2>How this compares with CRFB</h2>
        <p className="note">
          CRFB&apos;s <a href={CRFB_REFORMER_URL}>Social Security Reformer</a> does not publish its option figures as a
          table, so the comparison uses the numbers CRFB states in its posts. Gaps are reported, not tuned away.
          CRFB&apos;s figures rest on the 2025 Trustees Report, whose 75-year deficit was smaller, so the same option
          closes a larger share there.
        </p>
        <div className="tablewrap">
          <table className="sheet">
            <thead>
              <tr>
                <th>CRFB item</th>
                <th>Measure</th>
                <th>CRFB</th>
                <th>This page</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {data.crfb.map((r, i) => (
                <tr key={i} title={`${r.our_basis}. ${r.note}`}>
                  <td className="billtitle">{r.crfb_item}</td>
                  <td>{r.measure}</td>
                  <td>{r.crfb}</td>
                  <td>{r.ours}</td>
                  <td>
                    <a href={r.source_url}>CRFB</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <details>
          <summary>Why the two may differ, row by row</summary>
          <ul className="marked">
            {data.crfb.map((r, i) => (
              <li key={i}>
                <b>{r.crfb_item}, {r.measure.toLowerCase()}:</b> {r.note} ({r.our_basis})
              </li>
            ))}
          </ul>
        </details>
      </section>

      <section>
        <h2>How the ledger works</h2>
        <ul className="marked">
          <li>
            Baseline: income and cost rates from the <a href={TRUSTEES_URL}>2026 Trustees Report</a> (Table IV.B1),
            taxable payroll and the trust fund interest factor from Table VI.G1, reserves at the end of 2025 from Table VI.G2.
          </li>
          <li>
            Options: each option&apos;s year-by-year change in cost and income rates, from{" "}
            <a href={OCACT_INDEX_URL}>OCACT&apos;s provision tables</a>.
          </li>
          <li>
            Ledger: reserves grow at the Trustees&apos; interest factor plus each year&apos;s income minus cost. The
            funds run out in the first year reserves end negative.
          </li>
          <li>
            Checks: current law comes out at 2034 and 83% payable (Trustees: 2034, 83%), and the 75-year balance at
            −4.44% (Trustees: −4.42%). Each option&apos;s change in the balance matches OCACT&apos;s own figure to 0.01
            points, and its depletion year matches in 32 of 33 cases (one is a year early).
          </li>
          <li>
            Not modelled: interactions between options, effects on the rest of the budget, who gains and loses, and
            Medicare&apos;s trust fund. For the ten-year budget cost of payroll tax changes, see the payroll proposals on{" "}
            <a href="/explore">Explore</a>.
          </li>
        </ul>
      </section>
    </>
  );
}
