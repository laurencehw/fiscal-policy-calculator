"use client";
// The overlapping-generations explorer: three long-run levers, run on the engine.
import { useEffect, useRef, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { OLG_SLIDERS, olgFromQuery, olgToQuery, type OlgKey } from "@/lib/olg";
import type { OlgResult } from "@/lib/types";

const signed = (v: number, digits: number) => `${v > 0 ? "+" : v < 0 ? "-" : ""}${Math.abs(v).toFixed(digits)}`;
const BASE = Object.fromEntries(OLG_SLIDERS.map((s) => [s.key, s.base])) as Record<OlgKey, number>;

const PATHS = [
  ["gdp_path_pct", "GDP", "%"],
  ["capital_path_pct", "Capital stock", "%"],
  ["interest_path_ppts", "Interest rate", " pt"],
] as const;

type State = { status: "idle" | "running" } | { status: "done"; result: OlgResult } | { status: "error"; message: string };

export function Generations() {
  const [values, setValues] = useState<Record<OlgKey, number>>(BASE);
  const [state, setState] = useState<State>({ status: "idle" });
  const started = useRef(false);
  const latest = useRef(0);

  async function run(next: Record<OlgKey, number>) {
    const id = ++latest.current;
    setState({ status: "running" });
    window.history.replaceState(null, "", `${window.location.pathname}?${olgToQuery(next)}`);
    try {
      const response = await fetch("/api/olg", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(next),
      });
      const data = await response.json().catch(() => null);
      if (id !== latest.current) return;
      if (!response.ok) {
        setState({ status: "error", message: data?.error ?? "The model did not run. Try again in a moment." });
        return;
      }
      setState({ status: "done", result: data as OlgResult });
    } catch {
      if (id !== latest.current) return;
      setState({ status: "error", message: "Could not reach the site. Check your connection and try again." });
    }
  }

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const params = new URLSearchParams(window.location.search);
    const fromLink = olgFromQuery(params);
    setValues(fromLink);
    if (OLG_SLIDERS.some((s) => params.has(s.param))) void run(fromLink);
  }, []);

  const unchanged = OLG_SLIDERS.every((s) => Math.abs(values[s.key] - s.base) < 0.05);

  return (
    <>
      <form
        className="tailorform"
        onSubmit={(e) => {
          e.preventDefault();
          void run(values);
        }}
      >
        {OLG_SLIDERS.map((s) => (
          <label className="field" key={s.key}>
            <span>
              {s.label}: <b>{values[s.key].toFixed(s.step < 1 ? 1 : 0)}%</b>
              {Math.abs(values[s.key] - s.base) >= 0.05 ? ` (baseline ${s.base}%)` : " (baseline)"}
            </span>
            <input
              type="range"
              min={s.min}
              max={s.max}
              step={s.step}
              value={values[s.key]}
              onChange={(e) => setValues((cur) => ({ ...cur, [s.key]: Number(e.target.value) }))}
            />
            <small className="q">{s.help}</small>
          </label>
        ))}
        <div className="buttons">
          <button type="submit" disabled={state.status === "running" || unchanged}>
            {state.status === "running" ? "Running…" : "Run the model"}
          </button>
          <button type="button" className="quiet" onClick={() => setValues(BASE)} disabled={unchanged}>
            Back to baseline
          </button>
        </div>
      </form>
      <div aria-live="polite">
        {state.status === "running" ? <p className="note">Running on the engine. A cold start takes up to ten seconds.</p> : null}
        {state.status === "error" ? <p className="note warn">{state.message}</p> : null}
        {state.status === "done" ? <Result r={state.result} /> : null}
      </div>
    </>
  );
}

function Result({ r }: { r: OlgResult }) {
  const [path, setPath] = useState<(typeof PATHS)[number][0]>("gdp_path_pct");
  if (!r.changed || !r.long_run || !r.years) return <p className="note">These are the baseline rates, so nothing changes.</p>;
  if (!r.converged) {
    // An unsolved steady state is not an answer (it can read as GDP falling 99%), so nothing is shown.
    return (
      <p className="note warn">
        The model could not find a long-run equilibrium for these settings ({r.solver_status?.replace("_", " ")}), so no results are
        shown. Combinations that leave the government needing a negative tax on wages are the usual cause; try a smaller change.
      </p>
    );
  }
  const lr = r.long_run;
  const meta = PATHS.find((p) => p[0] === path) ?? PATHS[0];
  const series = r[path] ?? [];
  const rows = r.years.map((year, i) => ({ year, value: series[i] ?? null }));
  return (
    <>
      <section className="chart">
        <div className="head">
          <h2>Long run</h2>
          <span className="tag">new steady state against the baseline</span>
        </div>
        <div className="cycle four">
          <div className="stage">
            <span className="q">GDP</span>
            <span className="v">{signed(lr.gdp_pct, 2)}%</span>
          </div>
          <div className="stage">
            <span className="q">Capital stock</span>
            <span className="v">{signed(lr.capital_pct, 2)}%</span>
          </div>
          <div className="stage">
            <span className="q">Real wage</span>
            <span className="v">{signed(lr.wage_pct, 2)}%</span>
          </div>
          <div className="stage">
            <span className="q">Interest rate</span>
            <span className="v">{signed(lr.interest_rate_ppts, 2)} pt</span>
          </div>
        </div>
        <p className="note">
          Capital per unit of output moves from {lr.capital_output_baseline.toFixed(2)} to {lr.capital_output_reform.toFixed(2)}.
          {r.path_settles ? ` Thirty years in, GDP is ${signed(r.year_30_gdp_pct ?? 0, 2)}% from baseline.` : null}
        </p>
      </section>
      {r.path_settles ? (
      <section className="chart">
        <div className="head">
          <h2>Transition</h2>
          <span className="tag">{r.years.length} years from {r.years[0]}</span>
        </div>
        <div className="seg" role="group" aria-label="Path shown">
          {PATHS.map(([k, label]) => (
            <button key={k} type="button" aria-pressed={k === path} onClick={() => setPath(k)}>
              {label}
            </button>
          ))}
        </div>
        <div className="plot" role="img" aria-label={`${meta[1]}, change from baseline, ${r.years[0]} to ${r.years[r.years.length - 1]}`}>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="year" tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={{ stroke: "var(--rule)" }} minTickGap={24} />
              <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={false} width={56} tickFormatter={(v: number) => `${v.toFixed(1)}${meta[2]}`} />
              <ReferenceLine y={0} stroke="var(--ink)" />
              <Tooltip
                content={({ active, payload }) =>
                  active && payload?.length ? (
                    <div className="tip">
                      {(payload[0].payload as { year: number }).year}: {meta[1]} {signed(Number(payload[0].value ?? 0), 2)}
                      {meta[2]}
                    </div>
                  ) : null
                }
              />
              <Line dataKey="value" stroke="var(--accent)" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="note">
          The path assumes households re-plan each year at that year&rsquo;s prices, so the economy reaches its new long run within a few
          years. With forward-looking households and capital built up cohort by cohort, the adjustment would take decades; read the path
          as the direction of travel, not its speed.
        </p>
      </section>
      ) : (
        <section className="chart">
          <div className="head">
            <h2>Transition</h2>
            <span className="tag">not shown</span>
          </div>
          <p className="note warn">
            The model&rsquo;s year-by-year path from today to the long run does not settle where the long-run result says it should
            (GDP ends {signed(r.path_end_gdp_pct ?? 0, 1)}% from baseline against {signed(lr.gdp_pct, 1)}% in the long run), so the path
            is not shown until that is fixed. The long-run figures above and the burden by age below compare the two steady states and do
            not depend on it.
          </p>
        </section>
      )}
      {r.accounts ? <Accounts a={r.accounts} /> : null}
    </>
  );
}

function Accounts({ a }: { a: NonNullable<OlgResult["accounts"]> }) {
  return (
    <section className="chart">
      <div className="head">
        <h2>Who carries it</h2>
        <span className="tag">lifetime net taxes by age today</span>
      </div>
      <div className="cycle three">
        <div className="stage">
          <span className="q">Youngest workers (age 21)</span>
          <span className="v">{signed(a.newborn_burden_change, 3)}</span>
        </div>
        <div className="stage">
          <span className="q">Average across living ages</span>
          <span className="v">{signed(a.weighted_burden_change, 3)}</span>
          <span className="q">weighted by population</span>
        </div>
        <div className="stage">
          <span className="q">Shift to the young</span>
          <span className="v">{signed(a.generational_imbalance, 3)}</span>
          <span className="q">{a.generational_imbalance > 0 ? "more burden on the young" : "less burden on the young"}</span>
        </div>
      </div>
      <div className="plot" role="img" aria-label="Change in remaining lifetime net taxes by current age">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={a.by_age} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="age" tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={{ stroke: "var(--rule)" }} minTickGap={16} />
            <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={false} width={56} tickFormatter={(v: number) => v.toFixed(2)} />
            <ReferenceLine y={0} stroke="var(--ink)" />
            <Tooltip
              cursor={{ fill: "var(--grid)" }}
              content={({ active, payload }) =>
                active && payload?.length ? (
                  <div className="tip">
                    Age {(payload[0].payload as { age: number }).age}: {signed(Number(payload[0].value ?? 0), 3)}
                  </div>
                ) : null
              }
            />
            <Bar
              dataKey="change"
              isAnimationActive={false}
              shape={(props: { x?: number; y?: number; width?: number; height?: number; payload?: { change: number } }) => {
                const { x = 0, y = 0, width = 0, height = 0, payload } = props;
                // More lifetime tax shrinks the deficit, so it takes the "reduces" colour, as on Who pays.
                const fill = (payload?.change ?? 0) > 0 ? "var(--reduces)" : "var(--adds)";
                return <rect x={x} y={height < 0 ? y + height : y} width={width} height={Math.abs(height)} fill={fill} />;
              }}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <details>
        <summary>Table by age</summary>
        <div className="tablewrap">
          <table className="sheet">
            <thead>
              <tr>
                <th>Age today</th>
                <th>Baseline</th>
                <th>Reform</th>
                <th>Change</th>
              </tr>
            </thead>
            <tbody>
              {a.by_age.map((row) => (
                <tr key={row.age}>
                  <td>{row.age}</td>
                  <td>{row.baseline.toFixed(3)}</td>
                  <td>{row.reform.toFixed(3)}</td>
                  <td>{signed(row.change, 3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <p className="note">
        The present value of each cohort&rsquo;s remaining lifetime net taxes, in the model&rsquo;s own units, for each age alive at the start. A
        positive change means that cohort pays more over the rest of its life.
      </p>
    </section>
  );
}
