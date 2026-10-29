import type { Metadata } from "next";
import Link from "next/link";
import { evidence, scorecardEntries, tierOf, type Tier } from "@/lib/data";
import { money } from "@/lib/format";
import type { EvidenceSummary, ScorecardEntry } from "@/lib/types";

export const metadata: Metadata = {
  title: "Methods",
  description: "How the calculator scores a policy, the parameters it uses, and how far its numbers sit from published scores.",
};

function share(s: EvidenceSummary, key: "within_15pct" | "within_25pct"): string {
  return `${s[key]} of ${s.n}`;
}

const TIER_NAME: Record<Tier, string> = {
  out_of_sample: "Out-of-sample predictions",
  fitted: "Fitted to the published score",
  reconstruction: "Reconstructions, not fitted",
  retired: "Withdrawn targets",
};

const TIER_NOTE: Record<Tier, string> = {
  out_of_sample:
    "Built bottom-up from IRS filer counts, the CBO baseline and each module's revenue arithmetic. Nothing was tuned to these targets, and each was registered before it was first scored.",
  fitted:
    "A constant in the module was chosen so the model reproduces this score. Small errors here are by construction and say little about accuracy.",
  reconstruction:
    "Scored against a published figure no constant is fitted to. A miss here is a finding about the model.",
  retired:
    "The target turned out not to be a published score of this policy. The row stays on the record with the error it carried when withdrawn.",
};

function Benchmarks({ tier, rows }: { tier: Tier; rows: ScorecardEntry[] }) {
  const sorted = [...rows].sort((a, b) => a.abs_percent_difference - b.abs_percent_difference);
  return (
    <details>
      <summary>
        {TIER_NAME[tier]} ({rows.length})
      </summary>
      <p className="note">{TIER_NOTE[tier]}</p>
      <div className="tablescroll">
        <table className="sheet bench">
          <thead>
            <tr>
              <th scope="col">Policy</th>
              <th scope="col">Published</th>
              <th scope="col">Calculator</th>
              <th scope="col">Gap</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((e) => (
              <tr key={e.policy_id}>
                <td>
                  {e.policy_name}
                  <span className="cite">
                    {e.benchmark_url ? <a href={e.benchmark_url}>{e.official_source}</a> : e.official_source}
                    {e.benchmark_date ? `, ${e.benchmark_date}` : ""}
                  </span>
                </td>
                <td>
                  {e.published_range_low_billions !== null && e.published_range_high_billions !== null
                    ? `${money(e.published_range_low_billions)} to ${money(e.published_range_high_billions)}`
                    : money(e.official_10yr_billions)}
                </td>
                <td>{money(e.model_10yr_billions)}</td>
                <td>{e.abs_percent_difference.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export default function Methods() {
  const ev = evidence();
  const oos = ev.out_of_sample;
  const cal = ev.calibrated;
  const loo = ev.leave_one_out;
  const v = ev.data_vintages;
  const classes = Object.values(ev.out_of_sample_classes).sort((a, b) => a.mean_abs_error - b.mean_abs_error);
  const entries = scorecardEntries();
  const tiers: Tier[] = ["out_of_sample", "fitted", "reconstruction", "retired"];
  return (
    <>
      <header>
        <span className="eyebrow">Methods</span>
        <h1>How the calculator works</h1>
        <p className="sentence">
          A score is built in three steps, the way CBO and JCT build theirs. This page sets out each step, the
          numbers it rests on, and how far the results sit from published scores.
        </p>
      </header>

      <section>
        <h2>Three steps to a score</h2>
        <div className="cycle three">
          <div className="stage">
            <span className="q">1. Static</span>
            <p>
              The direct change in revenue, holding behaviour fixed. For a rate change: the change in rate, times the
              income above the threshold, times the number of filers it reaches. Only income above the threshold
              counts.
            </p>
          </div>
          <div className="stage">
            <span className="q">2. Behaviour</span>
            <p>
              People respond to a tax change by earning, reporting or timing income differently. For income tax the
              offset is half the static effect times the elasticity of taxable income (0.25), which shrinks a rise
              and a cut alike. Capital gains, corporate, trade and the other modules each carry their own response.
            </p>
          </div>
          <div className="stage">
            <span className="q">3. Economy (optional)</span>
            <p>
              The &ldquo;with economic feedback&rdquo; view runs the change through multipliers calibrated to the
              Federal Reserve&apos;s FRB/US model, books the revenue that follows from higher or lower output, and nets
              the interest on the extra debt. It has no long-run supply channel.
            </p>
          </div>
        </div>
      </section>

      <section>
        <h2>Key parameters</h2>
        <div className="tablescroll">
          <table className="sheet words">
            <thead>
              <tr>
                <th scope="col">Parameter</th>
                <th scope="col">Value</th>
                <th scope="col">Source</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>Elasticity of taxable income</td><td>0.25</td><td>Saez, Slemrod and Giertz (2012)</td></tr>
              <tr><td>Capital gains response to the tax rate</td><td>0.72 lasting, 1.20 in the first year, at a 22% reference rate</td><td>Dowd, McClelland and Muthitacharoen (2015); CRS R48562</td></tr>
              <tr><td>Spending multiplier, year 1</td><td>1.4, fading 25% a year</td><td>FRB/US calibration</td></tr>
              <tr><td>Tax multiplier, year 1</td><td>0.7</td><td>FRB/US calibration</td></tr>
              <tr><td>Demand effect kept each year</td><td>65%</td><td>FRB/US calibration (monetary offset)</td></tr>
              <tr><td>Crowding out</td><td>15% of the cumulative deficit</td><td>Literature estimate</td></tr>
              <tr><td>Revenue from extra output</td><td>25 cents per dollar</td><td>CBO</td></tr>
              <tr><td>Labour and capital shares</td><td>0.65 and 0.35</td><td>BLS</td></tr>
              <tr><td>Tariff income and payroll offset</td><td>0.244 in 2025 falling to 0.241 in 2035</td><td>JCT, via CBO&apos;s tariff model</td></tr>
              <tr><td>Corporate base</td><td>CBO&apos;s corporate receipts path, scaled to the tax base</td><td>CBO publication 59710; IRS SOI</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2>How close are the numbers?</h2>
        <p>
          There are two kinds of check, and they answer different questions, so they are never pooled into one
          accuracy figure.
        </p>
        <h3>Predictions nobody tuned</h3>
        <p>
          The honest test. Across {oos.n} published scores, mostly from CBO&apos;s <em>Options for Reducing the
          Deficit</em>, the calculator is off by {oos.mean_abs_error}% on average ({oos.median_abs_error}% for the
          middle case). {share(oos, "within_15pct")} land within 15% and {share(oos, "within_25pct")} within 25%. The
          error depends a great deal on the kind of policy:
        </p>
        <div className="tablescroll">
          <table className="sheet">
            <thead>
              <tr>
                <th scope="col">Kind of policy</th>
                <th scope="col">Cases</th>
                <th scope="col">Average gap</th>
                <th scope="col">Within 15%</th>
              </tr>
            </thead>
            <tbody>
              {classes.map((c) => (
                <tr key={c.label}>
                  <td>{c.label[0].toUpperCase() + c.label.slice(1)}</td>
                  <td>{c.n}</td>
                  <td>{c.mean_abs_error}%</td>
                  <td>{c.within_15pct}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h3>Reconstructions of published scores</h3>
        <p>
          For {cal.fitted.n} policies a module constant was fitted so the model reproduces the published score. Their
          average gap of {cal.fitted.mean_abs_error}% is low by construction. Holding in place the rows whose published
          target was later corrected, the same group reads {cal.fitted_held_in_place.mean_abs_error}% over{" "}
          {cal.fitted_held_in_place.n}.
        </p>
        <p>
          Another {cal.reconstruction.n} policies are scored against a published figure nothing is fitted to. Their
          average gap is {cal.reconstruction.mean_abs_error}% ({cal.reconstruction.median_abs_error}% for the middle
          case).
          <br />
          With the {cal.retired_targets.n} withdrawn targets held in place at the error they carried, it is{" "}
          {cal.reconstruction_retired_held_in_place.mean_abs_error}% over {cal.reconstruction_retired_held_in_place.n}.
        </p>
        <p>
          A third check refits each fitted module without one of its targets and asks whether it can put that target
          back. Across {loo.n} such cases the gap is {loo.mean_abs_error}% on average ({loo.not_cross_validatable} more
          cannot be tested this way).
        </p>
        <h3>Every benchmark</h3>
        {tiers.map((tier) => (
          <Benchmarks key={tier} tier={tier} rows={entries.filter((e) => tierOf(e) === tier)} />
        ))}
      </section>

      <section>
        <h2>Data</h2>
        <ul>
          <li>
            <b>CBO baseline, {v.cbo_baseline_vintage}.</b> Ten-year revenue, spending, deficits and the economic path,
            read from CBO&apos;s own published tables (<a href="https://github.com/US-CBO/cbo-data">US-CBO/cbo-data</a>).
            Every score is a change against this current-law baseline.
          </li>
          <li>
            <b>IRS Statistics of Income, tax years {v.irs_soi_tax_years.join(", ")}.</b> Filer counts, income and tax by
            income class and filing status. The latest year, {v.irs_soi_latest_tax_year}, sets the income-tax bases.
          </li>
          <li>
            <b>Census CPS household survey.</b> Tax units for the who-pays tables and the credits, reweighted to IRS
            totals for {v.microdata_calibration_year} ({v.microdata_returns_coverage_pct}% of returns,{" "}
            {v.microdata_agi_coverage_pct}% of income).
          </li>
          <li>
            <b>FRED.</b> Macroeconomic series from the St. Louis Fed.
          </li>
        </ul>
      </section>

      <section>
        <h2>How much to trust each part</h2>
        <ul>
          <li>
            <b>Core, checked against published scores:</b> revenue scoring with behaviour, the who-pays tables, and the
            view with economic feedback.
          </li>
          <li>
            <b>Specialised, narrower:</b> the policy-area modules (corporate, trade, estate, payroll, credits and the
            rest). Most are tuned to reproduce published scores, so agreement there is reconstruction, not
            independent confirmation.
          </li>
          <li>
            <b>Exploratory:</b> the bill tracker&apos;s reading of bill text. Treat it as a first pass.
          </li>
        </ul>
        <p>
          The full methods, every figure the model is checked against and its source, and the code are in the{" "}
          <a href="https://github.com/laurencehw/fiscal-policy-calculator/blob/main/docs/METHODOLOGY.md">repository</a>.
          See also <Link href="/about">About</Link>.
        </p>
      </section>
    </>
  );
}
