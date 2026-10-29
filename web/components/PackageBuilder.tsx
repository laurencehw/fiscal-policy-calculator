"use client";
// Build: tick policies, see the package's ten-year list-price total. State lives
// in ?policies=, the same parameter the Streamlit app's share links use.
import { useEffect, useMemo, useState } from "react";
import { cleanLabel, money } from "@/lib/format";
import { choose, covered, fromQuery, total } from "@/lib/package";
import type { BuildRow, ValuesArchetype } from "@/lib/types";

export function PackageBuilder({
  rows,
  scored,
  archetypes = [],
}: {
  rows: BuildRow[];
  scored: string[];
  archetypes?: ValuesArchetype[];
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [philosophy, setPhilosophy] = useState<ValuesArchetype | null>(null);
  const scoredIds = useMemo(() => new Set(scored), [scored]);

  function usePhilosophy(a: ValuesArchetype) {
    setPhilosophy(a);
    setSelected(fromQuery(rows, a.picks.map((p) => p.policy_id).join(",")));
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    // ?values=<id> is the app's share link for a philosophy; it resolves to its package.
    const a = archetypes.find((x) => x.id === params.get("values"));
    if (a && !params.get("policies")) {
      setPhilosophy(a);
      setSelected(fromQuery(rows, a.picks.map((p) => p.policy_id).join(",")));
    } else {
      setSelected(fromQuery(rows, params.get("policies")));
    }
  }, [rows, archetypes]);

  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.delete("policies");
    url.searchParams.delete("values");
    const rest = url.searchParams.toString();
    // Ids are [a-z0-9-], so the list needs no encoding; keep the commas readable.
    const query = [rest, selected.length ? `policies=${selected.join(",")}` : ""].filter(Boolean).join("&");
    window.history.replaceState(null, "", `${url.pathname}${query ? `?${query}` : ""}${url.hash}`);
  }, [selected]);

  const inside = covered(rows, selected);
  const sum = total(rows, selected);
  const areas = [...new Set(rows.map((r) => r.area))];
  const label = (id: string) => cleanLabel(rows.find((r) => r.build_id === id)?.label ?? id);

  function toggle(id: string) {
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : choose(rows, s, id)));
  }

  const edited =
    philosophy !== null &&
    [...philosophy.picks.map((p) => p.policy_id)].sort().join(",") !== [...selected].sort().join(",");

  return (
    <>
    {archetypes.length ? (
      <section className="values">
        <h2>Start from your values</h2>
        <p className="note">
          Pick a starting philosophy and the calculator chooses a package for it. The choice is mechanical: each policy
          carries tags for who pays, the size of government, the growth cost and the generations it falls on, and the
          same values always give the same package. It is a starting point, not a verdict; everything stays editable
          in the list below.
        </p>
        <div className="cards">
          {archetypes.map((a) => (
            <button
              key={a.id}
              type="button"
              className={`card${philosophy?.id === a.id ? " on" : ""}`}
              aria-pressed={philosophy?.id === a.id}
              onClick={() => usePhilosophy(a)}
            >
              <b>{a.name}</b>
              <span>{a.one_line}</span>
              <small>{a.chips.join(" · ")}</small>
            </button>
          ))}
        </div>
        {philosophy ? (
          <div className="whys" aria-live="polite">
            <p>
              <b>{philosophy.name}:</b> {philosophy.summary}. The package scores {money(philosophy.total_billions)}{" "}
              against a gap of {money(philosophy.gap_billions).replace("+", "")} to a deficit of{" "}
              {philosophy.target_pct_gdp.toFixed(1)}% of GDP.
              {philosophy.protected.length ? ` Protected: ${philosophy.protected.join(", ").toLowerCase()}.` : ""}
              {edited ? " You have since edited the list below." : ""}
            </p>
            <ol>
              {philosophy.picks.map((p) => (
                <li key={p.policy_id}>
                  <span className="whyname">
                    {cleanLabel(p.label)} <span className={`fig ${p.score > 0 ? "adds" : "reduces"}`}>{money(p.score)}</span>
                  </span>
                  <small>{p.why}</small>
                </li>
              ))}
            </ol>
          </div>
        ) : null}
      </section>
    ) : null}
    <div className="builder">
      <div className="buildlist">
        {areas.map((area) => (
          <fieldset key={area}>
            <legend>{area}</legend>
            {rows
              .filter((r) => r.area === area)
              .map((r) => {
                const by = inside.get(r.build_id);
                return (
                  <label key={r.build_id} className={by ? "covered" : undefined}>
                    <input
                      type="checkbox"
                      checked={selected.includes(r.build_id) || Boolean(by)}
                      disabled={Boolean(by)}
                      onChange={() => toggle(r.build_id)}
                    />
                    <span className="buildname">
                      {cleanLabel(r.label)}
                      <small>
                        {r.source}, {r.source_date}
                        {by ? ` · included in ${label(by)}` : ""}
                        {scoredIds.has(r.build_id) ? (
                          <>
                            {" · "}
                            <a href={`/explore/${r.build_id}`}>calculator&apos;s score</a>
                          </>
                        ) : null}
                      </small>
                    </span>
                    <span className={`fig ${r.score > 0 ? "adds" : "reduces"}`}>{money(r.score)}</span>
                  </label>
                );
              })}
          </fieldset>
        ))}
      </div>
      <aside className="buildtotal" aria-live="polite">
        <span className="eyebrow">Your package</span>
        <p className={`fig big ${sum > 0 ? "adds" : sum < 0 ? "reduces" : ""}`}>{money(sum)}</p>
        <p className="note">
          {selected.length === 0
            ? "Tick policies to add their ten-year figures."
            : `${selected.length} ${selected.length === 1 ? "policy" : "policies"}; ${
                sum > 0 ? "adds to" : sum < 0 ? "reduces" : "leaves unchanged"
              } the deficit over ten years.`}
        </p>
        {selected.length > 1 ? (
          <p className="note">
            This is the sum of each policy&apos;s published score on its own. Policies that touch the same tax base
            interact, so the package together can differ from the sum; this page does not measure that.
          </p>
        ) : null}
        {selected.length ? (
          <button type="button" onClick={() => setSelected([])}>
            Clear
          </button>
        ) : null}
      </aside>
    </div>
    </>
  );
}
