"use client";

import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { money, pct } from "@/lib/format";
import type { StatesData } from "@/lib/types";

const usd = (v: number) => `$${Math.round(v).toLocaleString("en-US")}`;
const incomeTick = (v: number) => (v >= 1_000_000 ? `$${v / 1_000_000}M` : `$${v / 1000}K`);
const SERIES = [
  ["federal_rate", "Federal", "var(--accent)"],
  ["state_rate", "State", "var(--muted)"],
  ["combined_rate", "Combined", "var(--ink)"],
] as const;

export function StateExplorer({ data }: { data: StatesData }) {
  const [code, setCode] = useState(data.states[0]?.code ?? "CA");
  const s = data.states.find((x) => x.code === code) ?? data.states[0];
  const rows = s.rate_curve.map((r) => ({ agi: r.agi, federal_rate: r.federal_rate * 100, state_rate: r.state_rate * 100, combined_rate: r.combined_rate * 100 }));
  return (
    <>
      <section className="chart">
        <div className="head">
          <h2>{s.name}</h2>
          <label className="tag">
            State{" "}
            <select value={code} onChange={(e) => setCode(e.target.value)}>
              {data.states.map((x) => (
                <option key={x.code} value={x.code}>
                  {x.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="cycle three">
          <div className="stage">
            <span className="q">State income tax</span>
            <span className="v">{!s.has_income_tax ? "None" : s.flat_rate !== null ? `${pct(s.flat_rate * 100, 2)} flat` : `Up to ${pct(s.top_rate * 100)}`}</span>
          </div>
          <div className="stage">
            <span className="q">Median household income</span>
            <span className="v">{usd(s.median_household_income)}</span>
          </div>
          <div className="stage">
            <span className="q">Average SALT deduction, itemizers</span>
            <span className="v">{usd(s.avg_salt_deduction_itemizers)}</span>
          </div>
        </div>
        <h3>Effective tax rate by income</h3>
        <div className="legend">
          {SERIES.map(([, label, color]) => (
            <span key={label} style={{ ["--c" as string]: color }}>
              {label}
            </span>
          ))}
        </div>
        <div className="plot" role="img" aria-label={`Federal, state and combined effective income tax rates by income in ${s.name}`}>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="agi" scale="log" domain={["dataMin", "dataMax"]} type="number" tickFormatter={incomeTick} tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={{ stroke: "var(--rule)" }} />
              <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={false} width={44} tickFormatter={(v: number) => `${v}%`} />
              <Tooltip
                content={({ active, payload }) =>
                  active && payload?.length ? (
                    <div className="tip">
                      {usd((payload[0].payload as { agi: number }).agi)}:{" "}
                      {payload.map((p) => `${p.name} ${Number(p.value).toFixed(1)}%`).join(", ")}
                    </div>
                  ) : null
                }
              />
              {SERIES.map(([key, label, color]) => (
                <Line key={key} dataKey={key} name={label} stroke={color} strokeWidth={2} strokeDasharray={key === "combined_rate" ? "5 3" : undefined} dot={false} isAnimationActive={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="tablewrap">
          <table className="sheet">
            <thead>
              <tr>
                <th>Income (AGI)</th>
                <th>Federal</th>
                <th>State</th>
                <th>Combined</th>
              </tr>
            </thead>
            <tbody>
              {s.rate_curve.map((r) => (
                <tr key={r.agi}>
                  <td>{usd(r.agi)}</td>
                  <td>{pct(r.federal_rate * 100)}</td>
                  <td>{pct(r.state_rate * 100)}</td>
                  <td>{pct(r.combined_rate * 100)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="note">
          Effective rate is income tax paid divided by AGI. {s.notes}
        </p>
      </section>

      <section className="chart">
        <div className="head">
          <h2>Lifting the SALT cap, state by state</h2>
          <span className="tag">per year</span>
        </div>
        <p className="note">
          The cap is ${data.salt_cap_baseline.toLocaleString("en-US")} in {data.year}, cut back toward $
          {data.salt_cap_reverted.toLocaleString("en-US")} for incomes above $
          {(data.salt_cap_phasedown_threshold ?? 0).toLocaleString("en-US")}. It returns to $
          {data.salt_cap_reverted.toLocaleString("en-US")} for everyone in {data.salt_cap_reversion_year}. The last column
          prices removing it then, at the same incomes.
        </p>
        <div className="tablewrap">
          <table className="sheet">
            <thead>
              <tr>
                <th>State</th>
                <th>Itemizers</th>
                <th>Combined state and local rate</th>
                <th>Filers above the cap</th>
                <th>Average deduction gain</th>
                <th>Federal deficit effect, {data.year}</th>
                <th>From {data.salt_cap_reversion_year}</th>
              </tr>
            </thead>
            <tbody>
              {data.states.map((x) => (
                <tr key={x.code}>
                  <td>{x.name}</td>
                  <td>{pct(x.pct_itemizers * 100)}</td>
                  <td>{pct(x.effective_salt_rate * 100)}</td>
                  <td>{filers(x.salt_cap_lift.affected_filers_millions)}</td>
                  <td>{usd(x.salt_cap_lift.avg_deduction_change)}</td>
                  <td>{money(-x.salt_cap_lift.federal_revenue_change_billions)}</td>
                  <td>{money(-x.salt_cap_lift_reverted.federal_revenue_change_billions)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

/** Filer counts: thousands below a million, so small states do not print 0.0M. */
function filers(millions: number): string {
  if (millions >= 1) return `${millions.toFixed(1)}M`;
  return `${Math.round(millions * 1000).toLocaleString("en-US")}K`;
}
