"use client";

import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { axisMoney, deficitPaths, pathGap, sum, trillions, type BaselineYear, type Effect } from "@/lib/baseline";
import { money } from "@/lib/format";

type Point = { year: number; law: number; plan: number };

function Chart({ rows, dollars, label }: { rows: Point[]; dollars: boolean; label: string }) {
  const format = (value: number) => (dollars ? axisMoney(value) : `${value.toFixed(0)}%`);
  return (
    <div className="plot" role="img" aria-label={label}>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="year" tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={{ stroke: "var(--rule)" }} interval="preserveStartEnd" minTickGap={8} />
          <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={false} width={52} tickFormatter={format} domain={[0, "auto"]} />
          <Tooltip
            content={({ active, payload }) =>
              active && payload?.length ? (
                <div className="tip">
                  FY{(payload[0].payload as Point).year}: current law {format((payload[0].payload as Point).law)}, this proposal{" "}
                  {format((payload[0].payload as Point).plan)}
                </div>
              ) : null
            }
          />
          <Line dataKey="law" name="Current law" stroke="var(--muted)" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line dataKey="plan" name="This proposal" stroke="var(--accent)" strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Deficit and debt under current law and under the proposal. Conventional: no feedback. */
export function BaselineChart({
  years,
  effects,
  headline,
}: {
  years: BaselineYear[];
  effects: Effect[];
  headline: number;
}) {
  const [share, setShare] = useState(false);
  const points = deficitPaths(years, effects);
  if (!points.length) return null;
  const deficit = points.map((row) => ({
    year: row.year,
    law: share ? (row.baselineDeficit / row.gdp) * 100 : row.baselineDeficit,
    plan: share ? (row.policyDeficit / row.gdp) * 100 : row.policyDeficit,
  }));
  const debt = points.map((row) => ({
    year: row.year,
    law: share ? (row.baselineDebt / row.gdp) * 100 : row.baselineDebt,
    plan: share ? (row.policyDebt / row.gdp) * 100 : row.policyDebt,
  }));
  const baselineTotal = sum(points.map((row) => row.baselineDeficit));
  const gap = pathGap(points);
  return (
    <section className="chart">
      <div className="head">
        <h2>On the baseline</h2>
        <div className="seg" role="group" aria-label="Units">
          <button type="button" aria-pressed={!share} onClick={() => setShare(false)}>
            Dollars
          </button>
          <button type="button" aria-pressed={share} onClick={() => setShare(true)}>
            Percent of GDP
          </button>
        </div>
      </div>
      <p className="units">
        Conventional, no feedback. Current law runs a {trillions(baselineTotal)} deficit over these years. This proposal
        changes that by {money(gap)}
        {Math.abs(gap - headline) < 0.05 ? "" : `, against a headline of ${money(headline)}`}.
      </p>
      <div className="legend">
        <span style={{ ["--c" as string]: "var(--muted)" }}>Current law</span>
        <span style={{ ["--c" as string]: "var(--accent)" }}>This proposal</span>
      </div>
      <p className="units">{share ? "Deficit, percent of GDP" : "Deficit, billions"}</p>
      <Chart rows={deficit} dollars={!share} label="Deficit under current law and under this proposal" />
      <p className="units">{share ? "Debt held by the public, percent of GDP" : "Debt held by the public, billions"}</p>
      <Chart rows={debt} dollars={!share} label="Debt held by the public under current law and under this proposal" />
    </section>
  );
}
