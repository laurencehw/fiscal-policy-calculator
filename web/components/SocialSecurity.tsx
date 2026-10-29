"use client";
// Social Security reform menu: pick OCACT options, see the share of the 75-year
// shortfall closed, the depletion year and the trust fund ratio path. State lives
// in ?options=, so a plan can be shared.
import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { orderIds, project, selectOption, type SSData, type SSProvision } from "@/lib/socialSecurity";

const NO_CHANGE = "none";

/** Heading over each set of alternative settings of one lever (as in the app). */
const GROUP_LABELS: Record<string, string> = {
  cola: "How the COLA is computed",
  initial_benefits: "Initial benefit formula",
  across_the_board: "Benefit level",
  retirement_age: "Normal retirement age",
  payroll_rate: "Payroll tax rate increase",
  taxable_maximum: "Earnings subject to the payroll tax",
  benefit_taxation: "Income tax on benefits",
};

function depletion(year: number | null): string {
  return year === null ? "Not before 2100" : String(year);
}

export function SocialSecurityMenu({ data }: { data: SSData }) {
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    const raw = new URLSearchParams(window.location.search).get("options");
    if (raw) setSelected(orderIds(data, raw.split(",")));
  }, [data]);

  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.delete("options");
    const rest = url.searchParams.toString();
    const query = [rest, selected.length ? `options=${selected.join(",")}` : ""].filter(Boolean).join("&");
    window.history.replaceState(null, "", `${url.pathname}${query ? `?${query}` : ""}${url.hash}`);
  }, [selected]);

  const baseline = useMemo(() => project(data), [data]);
  const plan = useMemo(() => project(data, selected), [data, selected]);
  const byId = useMemo(() => new Map(data.provisions.map((p) => [p.provision_id, p])), [data]);

  const chart = baseline.years.map((year, i) => ({
    year,
    law: Math.round(baseline.trustFundRatio[i]),
    plan: selected.length ? Math.round(plan.trustFundRatio[i]) : undefined,
  }));

  const delta =
    selected.length && plan.depletionYear && baseline.depletionYear
      ? plan.depletionYear - baseline.depletionYear
      : null;

  function groupChoice(group: string, members: SSProvision[]) {
    const current = members.find((p) => selected.includes(p.provision_id))?.provision_id ?? NO_CHANGE;
    return (
      <fieldset key={group}>
        <legend>{GROUP_LABELS[group] ?? group} (choose one)</legend>
        <label>
          <input
            type="radio"
            name={`ss-${group}`}
            checked={current === NO_CHANGE}
            onChange={() => setSelected((s) => s.filter((x) => byId.get(x)?.exclusive_group !== group))}
          />
          <span>No change</span>
        </label>
        {members.map((p) => (
          <label key={p.provision_id}>
            <input
              type="radio"
              name={`ss-${group}`}
              checked={current === p.provision_id}
              onChange={() => setSelected((s) => selectOption(data, s.filter((x) => x !== p.provision_id), p.provision_id))}
            />
            <span title={p.description}>{p.label}</span>
          </label>
        ))}
      </fieldset>
    );
  }

  return (
    <>
      <div className="ssgrid">
        <div className="ssmenu">
          <span className="eyebrow">Options</span>
          {Object.entries(data.categories).map(([category, heading]) => {
            const members = data.provisions.filter((p) => p.category === category);
            if (!members.length) return null;
            const groups = [...new Set(members.filter((p) => p.exclusive_group).map((p) => p.exclusive_group))];
            const singles = members.filter((p) => !p.exclusive_group);
            const count = members.filter((p) => selected.includes(p.provision_id)).length;
            return (
              <details key={category} open={count > 0 || undefined}>
                <summary>
                  {heading}
                  {count ? ` (${count})` : ""}
                </summary>
                {groups.map((g) => groupChoice(g, members.filter((p) => p.exclusive_group === g)))}
                {singles.map((p) => (
                  <label key={p.provision_id} className="single">
                    <input
                      type="checkbox"
                      checked={selected.includes(p.provision_id)}
                      onChange={() => setSelected((s) => selectOption(data, s, p.provision_id))}
                    />
                    <span title={p.description}>{p.label}</span>
                  </label>
                ))}
              </details>
            );
          })}
          {selected.length ? (
            <button type="button" onClick={() => setSelected([])}>
              Clear all
            </button>
          ) : null}
        </div>

        <div className="ssresult" aria-live="polite">
          <div className="cycle four">
            <div className="stage">
              <span className="q">75-year shortfall closed</span>
              <span className="v">{Math.round(plan.shareClosed * 100)}%</span>
            </div>
            <div className="stage">
              <span className="q">Trust funds run out</span>
              <span className="v">
                {depletion(plan.depletionYear)}
                {delta !== null ? <small> {delta ? `${delta > 0 ? "+" : ""}${delta} yrs` : "no change"}</small> : null}
              </span>
            </div>
            <div className="stage">
              <span className="q">Benefit cut when they do</span>
              <span className="v">{plan.cutAtDepletion === null ? "None" : `${Math.round(plan.cutAtDepletion * 100)}%`}</span>
            </div>
            <div className="stage">
              <span className="q">75-year balance, % of payroll</span>
              <span className="v">
                {`${plan.actuarialBalance > 0 ? "+" : plan.actuarialBalance < 0 ? "\u2212" : ""}${Math.abs(plan.actuarialBalance).toFixed(2)}`}
              </span>
            </div>
          </div>
          <p className="cyclenote">
            {selected.length
              ? `Sum of ${selected.length} separately scored OCACT ${selected.length === 1 ? "option" : "options"}, without interactions.`
              : "Current law. Pick options on the left to build a plan."}
          </p>

          <section className="chart">
            <div className="head">
              <span className="tag">Trust fund ratio</span>
            </div>
            <p className="units">Reserves at the start of each year as a percent of that year&apos;s cost</p>
            <div className="plot" role="img" aria-label="Trust fund ratio by year, current law and your plan">
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={chart} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke="var(--grid)" vertical={false} />
                  <XAxis dataKey="year" tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={{ stroke: "var(--rule)" }} interval={9} />
                  <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={false} width={44} tickFormatter={(v: number) => `${v}%`} />
                  <Tooltip
                    content={({ active, payload, label }) =>
                      active && payload?.length ? (
                        <div className="tip">
                          {label}:{" "}
                          {payload.map((p) => `${p.name} ${p.value}%`).join(" · ")}
                        </div>
                      ) : null
                    }
                  />
                  <Legend wrapperStyle={{ fontSize: 13, color: "var(--muted)" }} />
                  {baseline.depletionYear ? (
                    <ReferenceLine
                      x={baseline.depletionYear}
                      stroke="var(--warn)"
                      strokeDasharray="2 3"
                      label={{
                        value: `Current law runs out ${baseline.depletionYear}`,
                        position: "insideTopLeft",
                        fill: "var(--warn)",
                        fontSize: 12,
                        fontFamily: "var(--data)",
                      }}
                    />
                  ) : null}
                  {selected.length && plan.depletionYear && plan.depletionYear !== baseline.depletionYear ? (
                    <ReferenceLine
                      x={plan.depletionYear}
                      stroke="var(--accent)"
                      strokeDasharray="2 3"
                      label={{ value: `Plan runs out ${plan.depletionYear}`, position: "insideTopRight", fill: "var(--accent)", fontSize: 12, fontFamily: "var(--data)" }}
                    />
                  ) : null}
                  <Line type="monotone" dataKey="law" name="Current law" stroke="var(--ink)" strokeWidth={1.5} strokeDasharray={selected.length ? "4 4" : undefined} dot={false} isAnimationActive={false} />
                  {selected.length ? (
                    <Line type="monotone" dataKey="plan" name="Your plan" stroke="var(--accent)" strokeWidth={2} dot={false} isAnimationActive={false} />
                  ) : null}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>
        </div>
      </div>

      {selected.length ? (
        <section>
          <h2>Your options</h2>
          <div className="tablewrap">
            <table className="sheet">
              <thead>
                <tr>
                  <th>Option</th>
                  <th>Change in balance</th>
                  <th>Share of shortfall</th>
                  <th>Runs out (alone)</th>
                  <th>OCACT</th>
                </tr>
              </thead>
              <tbody>
                {selected.map((id) => {
                  const p = byId.get(id)!;
                  return (
                    <tr key={id}>
                      <td className="billtitle">{p.label}</td>
                      <td>{`${p.ocact_change_actuarial_balance > 0 ? "+" : p.ocact_change_actuarial_balance < 0 ? "\u2212" : ""}${Math.abs(p.ocact_change_actuarial_balance).toFixed(2)}`}</td>
                      <td>{Math.round((p.ocact_change_actuarial_balance / -data.trustees.actuarial_balance) * 100)}%</td>
                      <td>{p.ocact_depletion_year ?? "after 2100"}</td>
                      <td>
                        <a href={p.source_url}>run {p.ocact_run}</a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </>
  );
}
