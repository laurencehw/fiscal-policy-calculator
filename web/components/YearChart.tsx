"use client";

import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { money } from "@/lib/format";

type Row = { year: number; value: number };

/** Annual deficit effect, one bar per fiscal year; colour says which way it moves the deficit. */
export function YearChart({ rows, label }: { rows: Row[]; label: string }) {
  return (
    <div className="plot" role="img" aria-label={label}>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 8 }} barCategoryGap="24%">
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="year" tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={{ stroke: "var(--rule)" }} interval="preserveStartEnd" minTickGap={8} />
          <YAxis
            tick={{ fill: "var(--muted)", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={64}
            tickFormatter={(v: number) => `${v < 0 ? "-" : ""}$${Math.abs(v).toLocaleString("en-US")}B`}
          />
          <ReferenceLine y={0} stroke="var(--ink)" />
          <Tooltip
            cursor={{ fill: "var(--grid)" }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <div className="tip">
                  FY{(payload[0].payload as Row).year}: {money((payload[0].payload as Row).value)}
                </div>
              ) : null
            }
          />
          <Bar
            dataKey="value"
            maxBarSize={44}
            isAnimationActive={false}
            shape={(props: { x?: number; y?: number; width?: number; height?: number; payload?: Row }) => {
              const { x = 0, y = 0, width = 0, height = 0, payload } = props;
              const fill = (payload?.value ?? 0) > 0 ? "var(--adds)" : "var(--reduces)";
              return <rect x={x} y={height < 0 ? y + height : y} width={width} height={Math.abs(height)} fill={fill} />;
            }}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
