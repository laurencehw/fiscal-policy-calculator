"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { dollars, money, pct } from "@/lib/format";
import type { Distribution } from "@/lib/types";

const GROUPINGS = [
  ["quintile", "Quintiles"],
  ["decile", "Deciles"],
  ["jct_dollar", "Income brackets"],
] as const;

const REASONS: Record<string, string> = {
  not_a_tax_policy: "This is a spending or sector policy, so there is no tax table by income group.",
  not_representable:
    "The distribution engine cannot yet represent this kind of policy household by household (for example estate tax, tariffs, international or enforcement provisions). An all-zero table would look flat and be wrong, so none is shown.",
};

/** Who pays, by income group, in the first year. Tax change is in tax terms: positive means people pay more. */
export function WhoPays({ dist }: { dist: Distribution }) {
  const [key, setKey] = useState<(typeof GROUPINGS)[number][0]>("quintile");
  if (!dist.available) {
    return <p className="note">{REASONS[dist.reason ?? ""] ?? "No distribution table for this policy."}</p>;
  }
  const g = dist.groupings[key] ?? dist.groupings.quintile;
  if (!g) return null;
  const rows = g.groups.map((r) => ({ name: r.name.replace(/ Quintile| Decile/, ""), value: r.avg_tax_change }));
  return (
    <>
      <div className="seg" role="group" aria-label="Income grouping">
        {GROUPINGS.map(([k, label]) => (
          <button key={k} type="button" aria-pressed={k === key} onClick={() => setKey(k)}>
            {label}
          </button>
        ))}
      </div>
      <div className="cycle three">
        <div className="stage">
          <span className="q">Total tax change, {g.year}</span>
          <span className="v">{money(g.total_tax_change_billions)}</span>
          <span className="q">{g.total_tax_change_billions > 0 ? "people pay more" : g.total_tax_change_billions < 0 ? "people pay less" : "no change"}</span>
        </div>
        <div className="stage">
          <span className="q">Returns paying more</span>
          <span className="v">{pct(g.pct_with_increase)}</span>
        </div>
        <div className="stage">
          <span className="q">Returns paying less</span>
          <span className="v">{pct(g.pct_with_decrease)}</span>
        </div>
      </div>
      <div className="plot" role="img" aria-label={`Average tax change per return by income group, ${g.year}`}>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: "var(--muted)", fontSize: 11 }} tickLine={false} axisLine={{ stroke: "var(--rule)" }} interval={0} />
            <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={false} width={64} tickFormatter={(v: number) => dollars(v)} />
            <ReferenceLine y={0} stroke="var(--ink)" />
            <Tooltip
              cursor={{ fill: "var(--grid)" }}
              content={({ active, payload }) =>
                active && payload?.length ? (
                  <div className="tip">
                    {(payload[0].payload as { name: string }).name}: {dollars((payload[0].payload as { value: number }).value)} per return
                  </div>
                ) : null
              }
            />
            <Bar
              dataKey="value"
              isAnimationActive={false}
              shape={(props: { x?: number; y?: number; width?: number; height?: number; payload?: { value: number } }) => {
                const { x = 0, y = 0, width = 0, height = 0, payload } = props;
                // Paying more shrinks the deficit, so it takes the "reduces" colour.
                const fill = (payload?.value ?? 0) > 0 ? "var(--reduces)" : "var(--adds)";
                return <rect x={x} y={height < 0 ? y + height : y} width={width} height={Math.abs(height)} fill={fill} />;
              }}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="tablewrap">
        <table className="sheet">
          <thead>
            <tr>
              <th>Income group</th>
              <th>Returns</th>
              <th>Average change</th>
              <th>Share of income</th>
              <th>Share of total</th>
              <th>Paying more</th>
              <th>Paying less</th>
              <th>Tax rate before</th>
              <th>Tax rate after</th>
            </tr>
          </thead>
          <tbody>
            {g.groups.map((r) => (
              <tr key={r.name}>
                <td>{r.name}</td>
                <td>{r.returns_millions.toFixed(1)}M</td>
                <td>{dollars(r.avg_tax_change)}</td>
                <td>{pct(r.pct_of_income, 2)}</td>
                <td>{pct(r.share_of_total * 100)}</td>
                <td>{pct(r.pct_with_increase)}</td>
                <td>{pct(r.pct_with_decrease)}</td>
                <td>{pct(r.baseline_etr * 100)}</td>
                <td>{pct(r.new_etr * 100)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="note">
        {g.engine === "microsim"
          ? "Return-level microsimulation on CPS ASEC tax units calibrated to IRS data: the validated distributional tier."
          : "Approximate bracket method: this policy cannot run through the return-level microsimulation, so read the shape as directional rather than as a validated table."}{" "}
        Groups are ranked by adjusted gross income per return. Average change is in dollars per return; positive means the group pays more tax.
      </p>
    </>
  );
}
