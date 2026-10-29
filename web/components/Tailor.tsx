"use client";
// Tailor: describe a rate change, score it on the engine, share the link.
import { useEffect, useRef, useState } from "react";
import { ResultSections } from "@/components/ResultSections";
import { Checked, YearTable } from "@/components/ScoreParts";
import { YearChart } from "@/components/YearChart";
import { direction, money } from "@/lib/format";
import { DEFAULT_INPUT, RATE_MAX, RATE_MIN, WHO_CHOICES, describe, fromQuery, toQuery, type TailorInput } from "@/lib/tailor";
import type { ScoreResult, Views } from "@/lib/types";

type ViewsState = { status: "idle" | "loading" } | { status: "done"; views: Views } | { status: "error"; message: string };

type State = { status: "idle" } | { status: "scoring" } | { status: "done"; result: ScoreResult; input: TailorInput } | { status: "error"; message: string };

export function Tailor() {
  const [input, setInput] = useState<TailorInput>(DEFAULT_INPUT);
  const [state, setState] = useState<State>({ status: "idle" });
  const [views, setViews] = useState<ViewsState>({ status: "idle" });
  const started = useRef(false);
  // Only the latest run may write results; an older answer arriving late is dropped.
  const latest = useRef(0);

  async function score(next: TailorInput) {
    const id = ++latest.current;
    setState({ status: "scoring" });
    setViews({ status: "idle" });
    window.history.replaceState(null, "", `${window.location.pathname}?${toQuery(next)}`);
    try {
      const response = await fetch("/api/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(next),
      });
      const data = await response.json().catch(() => null);
      if (id !== latest.current) return;
      if (!response.ok) {
        setState({ status: "error", message: data?.error ?? "Scoring failed. Try again in a moment." });
        return;
      }
      setState({ status: "done", result: data as ScoreResult, input: next });
      void loadViews(next, id);
    } catch {
      if (id !== latest.current) return;
      setState({ status: "error", message: "Could not reach the site. Check your connection and try again." });
    }
  }

  // The detail sections take a few seconds more (the distribution runs on every
  // tax return in the sample), so they load after the headline is on screen.
  async function loadViews(next: TailorInput, id: number) {
    setViews({ status: "loading" });
    try {
      const response = await fetch("/api/views", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(next),
      });
      const data = await response.json().catch(() => null);
      if (id !== latest.current) return;
      if (!response.ok) {
        setViews({ status: "error", message: data?.error ?? "The detail views did not load." });
        return;
      }
      setViews({ status: "done", views: data as Views });
    } catch {
      if (id !== latest.current) return;
      setViews({ status: "error", message: "The detail views did not load. Check your connection." });
    }
  }

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const { input: fromLink, run } = fromQuery(new URLSearchParams(window.location.search));
    setInput(fromLink);
    if (run) void score(fromLink);
  }, []);

  const set = (patch: Partial<TailorInput>) =>
    setInput((cur) => {
      const next = { ...cur, ...patch };
      if (next.kind === "corporate") next.who = 0;
      else if (patch.kind === "income" && cur.kind === "corporate") next.who = DEFAULT_INPUT.who;
      return next;
    });

  return (
    <>
      <form
        className="tailorform"
        onSubmit={(e) => {
          e.preventDefault();
          if (input.rate !== 0) void score(input);
        }}
      >
        <fieldset>
          <legend>Tax</legend>
          <label>
            <input type="radio" name="kind" checked={input.kind === "income"} onChange={() => set({ kind: "income" })} />{" "}
            Individual income tax
          </label>
          <label>
            <input type="radio" name="kind" checked={input.kind === "corporate"} onChange={() => set({ kind: "corporate" })} />{" "}
            Corporate income tax
          </label>
        </fieldset>
        <label className="field">
          <span>Rate change, percentage points</span>
          <input
            type="number"
            min={RATE_MIN}
            max={RATE_MAX}
            step={0.1}
            value={input.rate}
            onChange={(e) => set({ rate: Number(e.target.value) })}
            required
          />
        </label>
        {input.kind === "income" ? (
          <label className="field">
            <span>Who pays it</span>
            <select value={input.who} onChange={(e) => set({ who: Number(e.target.value) })}>
              {WHO_CHOICES.map((c) => (
                <option key={c.token} value={c.dollars}>
                  {c.label}
                </option>
              ))}
              {WHO_CHOICES.some((c) => c.dollars === input.who) ? null : (
                <option value={input.who}>Above ${input.who.toLocaleString("en-US")}</option>
              )}
            </select>
          </label>
        ) : null}
        <label className="field">
          <span>Years in effect</span>
          <input
            type="number"
            min={1}
            max={10}
            step={1}
            value={input.duration}
            onChange={(e) => set({ duration: Math.max(1, Math.min(10, Math.trunc(Number(e.target.value) || 1))) })}
          />
        </label>
        <button type="submit" disabled={state.status === "scoring" || input.rate === 0}>
          {state.status === "scoring" ? "Scoring…" : "Score it"}
        </button>
      </form>

      <div aria-live="polite">
        {state.status === "scoring" ? (
          <p className="note">Scoring on the engine. The first request after a quiet spell takes up to ten seconds.</p>
        ) : null}
        {state.status === "error" ? <p className="note warn">{state.message}</p> : null}
        {state.status === "done" ? <Result result={state.result} input={state.input} /> : null}
      </div>
      {state.status === "done" ? (
        <div aria-live="polite">
          {views.status === "loading" ? <p className="note">Loading who pays, economic effects and other models…</p> : null}
          {views.status === "error" ? <p className="note warn">{views.message}</p> : null}
          {views.status === "done" ? <ResultSections views={views.views} /> : null}
        </div>
      ) : null}
    </>
  );
}

function Result({ result, input }: { result: ScoreResult; input: TailorInput }) {
  const headline = result.ten_year_deficit_impact;
  const dyn = result.dynamic_adjusted_impact;
  const name = describe(input);
  return (
    <section className="tailorresult">
      <span className="eyebrow">
        {result.budget_window} · CBO {result.baseline_vintage} baseline
      </span>
      <h2>{name}</h2>
      <div className="headline">
        <div className="stage">
          <span className="q">Ten-year deficit effect, conventional</span>
          <span className={`v ${headline > 0 ? "adds" : "reduces"}`}>{money(headline)}</span>
          <span className="q">{direction(headline)}</span>
        </div>
        <div className="stage">
          <span className="q">With macroeconomic feedback and debt service</span>
          <span className="v">{dyn === null ? "Not available" : money(dyn)}</span>
          <span className="q">{result.dynamic_model ?? result.error_message ?? ""}</span>
        </div>
      </div>
      <Checked cred={result.credibility} />
      <section className="chart">
        <div className="head">
          <h2>Year by year</h2>
          <span className="tag">billions, conventional</span>
        </div>
        <YearChart
          rows={result.year_by_year.map((row) => ({ year: row.year, value: row.final_effect }))}
          label={`Annual deficit effect of ${name}, ${result.budget_window}`}
        />
        <YearTable c={result} d={result} />
      </section>
      <p className="note">
        <a href={`/tailor?${toQuery(input)}`}>Link to this result</a>. It opens the same run here and in the
        current app.
      </p>
    </section>
  );
}
