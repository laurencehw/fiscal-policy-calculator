"use client";

import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { money } from "@/lib/format";
import type { Economic } from "@/lib/types";

const signed = (v: number, digits: number) => `${v > 0 ? "+" : v < 0 ? "-" : ""}${Math.abs(v).toFixed(digits)}`;

/** The macro paths behind the dynamic score: GDP, jobs, interest rates, and the budget feedback they produce. */
export function EconomicEffects({ econ }: { econ: Economic }) {
  if (!econ.available) return <p className="note">The macroeconomic model did not run for this policy.</p>;
  const rows = econ.years.map((year, i) => ({ year, gdp: econ.gdp_level_pct[i] }));
  const peakJobs = econ.employment_millions.reduce((a, b) => (Math.abs(b) > Math.abs(a) ? b : a), 0);
  return (
    <>
      <div className="cycle four">
        <div className="stage">
          <span className="q">GDP, summed over the window</span>
          <span className="v">{signed(econ.gdp_percent_years, 2)}</span>
          <span className="q">percent-years</span>
        </div>
        <div className="stage">
          <span className="q">Jobs at the largest effect</span>
          <span className="v">{signed(peakJobs * 1000, 0)}K</span>
        </div>
        <div className="stage">
          <span className="q">Deficit effect of the GDP change</span>
          <span className="v">{money(-econ.revenue_feedback_billions)}</span>
          <span className="q">{econ.revenue_feedback_billions < 0 ? "less tax collected" : "more tax collected"}</span>
        </div>
        <div className="stage">
          <span className="q">Deficit effect of interest on the debt</span>
          <span className="v">{money(econ.debt_service_billions)}</span>
          <span className="q">{econ.debt_service_billions < 0 ? "less debt, less interest" : "more debt, more interest"}</span>
        </div>
      </div>
      <div className="plot" role="img" aria-label={`GDP level, percent difference from baseline, ${econ.years[0]} to ${econ.years[econ.years.length - 1]}`}>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="year" tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={{ stroke: "var(--rule)" }} />
            <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={false} width={56} tickFormatter={(v: number) => `${v.toFixed(2)}%`} />
            <ReferenceLine y={0} stroke="var(--ink)" />
            <Tooltip
              content={({ active, payload }) =>
                active && payload?.length ? (
                  <div className="tip">
                    FY{(payload[0].payload as { year: number }).year}: GDP {signed((payload[0].payload as { gdp: number }).gdp, 3)}%
                  </div>
                ) : null
              }
            />
            <Line dataKey="gdp" stroke="var(--accent)" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="tablewrap">
        <table className="sheet">
          <thead>
            <tr>
              <th>Fiscal year</th>
              <th>GDP level</th>
              <th>Jobs</th>
              <th>Unemployment</th>
              <th>10-year rate</th>
              <th>GDP change, deficit</th>
              <th>Interest, deficit</th>
            </tr>
          </thead>
          <tbody>
            {econ.years.map((year, i) => (
              <tr key={year}>
                <td>{year}</td>
                <td>{signed(econ.gdp_level_pct[i], 3)}%</td>
                <td>{signed(econ.employment_millions[i] * 1000, 0)}K</td>
                <td>{signed(econ.unemployment_rate_ppts[i], 2)} pt</td>
                <td>{signed(econ.long_rate_ppts[i], 2)} pt</td>
                <td>{money(-econ.revenue_feedback_by_year[i])}</td>
                <td>{money(econ.debt_service_by_year[i])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="note">
        {econ.model}. Demand effects fade over five to seven years as monetary policy responds; there is no supply-side channel. The
        dynamic score is the conventional score, plus the deficit effects of the GDP change and of interest on the debt:{" "}
        {money(econ.conventional_billions)} {money(-econ.revenue_feedback_billions).replace(/^([+-])/, "$1 ")} {money(econ.debt_service_billions).replace(/^([+-])/, "$1 ")} ={" "}
        {money(econ.dynamic_total_billions)}.
      </p>
    </>
  );
}
