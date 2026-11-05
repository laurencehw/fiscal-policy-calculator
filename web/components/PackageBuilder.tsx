"use client";
// Build: tick policies, see the package's ten-year list-price total. State lives
// in ?policies=, the same parameter the Streamlit app's share links use.
import { useEffect, useState } from "react";
import { EstimateTag } from "@/components/EstimateTag";
import { PackageSummary } from "@/components/PackageSummary";
import { cleanLabel, money, shortLabel } from "@/lib/format";
import type { EstimateIdentity } from "@/lib/identity";
import { addToPackage, calculatorGap, choose, covered, fromQuery, replacedBy, targetShare, undoSelection } from "@/lib/package";
import type { BuildRow, ValuesArchetype } from "@/lib/types";

export function PackageBuilder({
  rows,
  calculator,
  identities,
  packageIdentity,
  archetypes = [],
}: {
  rows: BuildRow[];
  /** The calculator's ten-year conventional score by build id, where it scores the policy. */
  calculator: Record<string, number>;
  identities: Record<string, { published: EstimateIdentity; model: EstimateIdentity | null }>;
  packageIdentity: EstimateIdentity;
  archetypes?: ValuesArchetype[];
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [philosophy, setPhilosophy] = useState<ValuesArchetype | null>(null);
  const [ready, setReady] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [previous, setPrevious] = useState<string[] | null>(null);

  function usePhilosophy(a: ValuesArchetype) {
    setPhilosophy(a);
    setSelected(fromQuery(rows, a.picks.map((p) => p.policy_id).join(",")));
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const nameOf = (policyId: string) => cleanLabel(rows.find((r) => r.build_id === policyId)?.label ?? policyId);
    // ?values=<id> is the app's share link for a philosophy; it resolves to its package.
    const a = archetypes.find((x) => x.id === params.get("values"));
    const add = params.get("add");
    if (a && !params.get("policies") && !add) {
      setPhilosophy(a);
      setSelected(fromQuery(rows, a.picks.map((p) => p.policy_id).join(",")));
    } else {
      const stored = readStored();
      let base = fromQuery(rows, params.get("policies") ?? stored);
      if (add) {
        const result = addToPackage(rows, base, add);
        if (result.replaced.length) {
          setPrevious(base);
          setNotice(`Replaced ${nameOf(result.replaced[0])} with ${nameOf(add)}. These are alternatives.`);
        }
        base = result.selected;
      }
      setSelected(base);
    }
    setReady(true);
  }, [rows, archetypes]);

  useEffect(() => {
    if (!ready) return;
    writeStored(selected.join(","));
    const url = new URL(window.location.href);
    url.searchParams.delete("policies");
    url.searchParams.delete("values");
    url.searchParams.delete("add");
    const rest = url.searchParams.toString();
    // Ids are [a-z0-9-], so the list needs no encoding; keep the commas readable.
    const query = [rest, selected.length ? `policies=${selected.join(",")}` : ""].filter(Boolean).join("&");
    window.history.replaceState(null, "", `${url.pathname}${query ? `?${query}` : ""}${url.hash}`);
  }, [selected, ready]);

  const inside = covered(rows, selected);
  const areas = [...new Set(rows.map((r) => r.area))];
  const label = (id: string) => cleanLabel(rows.find((r) => r.build_id === id)?.label ?? id);

  function toggle(id: string) {
    if (selected.includes(id)) {
      setSelected(selected.filter((other) => other !== id));
      return;
    }
    const next = choose(rows, selected, id);
    const swapped = replacedBy(rows, selected, next);
    if (swapped.length) {
      setPrevious(selected);
      setNotice(`Replaced ${label(swapped[0].dropped)} with ${label(swapped[0].added)}. These are alternatives.`);
    }
    setSelected(next);
  }

  function undo() {
    if (!previous) return;
    setSelected(undoSelection(previous));
    setPrevious(null);
    setNotice(null);
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
          Pick a starting philosophy and the calculator chooses a package to match. The choice is mechanical. Each
          policy carries tags for who pays, the size of government, the growth cost and the generations it falls on,
          and the same values always give the same package. Treat the result as a place to start; everything stays
          editable in the list below.
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
          <div className="whys">
            <p>
              <b>{philosophy.name}:</b> {philosophy.picks.length} policies,{" "}
              {Math.round(targetShare(philosophy.total_billions, philosophy.gap_billions) * 100)}% of the target.
              {edited ? " You have since edited the list below." : ""}
            </p>
            <details>
              <summary>Why these choices?</summary>
            <p>
              {philosophy.summary}. The package scores {money(philosophy.total_billions)} against a gap of{" "}
              {money(philosophy.gap_billions).replace("+", "")} to a deficit of {philosophy.target_pct_gdp.toFixed(1)}% of
              GDP.
              {philosophy.protected.length ? ` Protected: ${philosophy.protected.join(", ").toLowerCase()}.` : ""}
            </p>
            <ol>
              {philosophy.picks.map((p) => (
                <li key={p.policy_id}>
                  <span className="whyname">
                    {cleanLabel(p.label)}{" "}
                    <span className={`fig ${p.score > 0 ? "adds" : "reduces"}`}>{money(p.score)}</span>
                    {identities[p.policy_id] ? (
                      <>
                        {" "}
                        <EstimateTag identity={identities[p.policy_id].published} short />
                      </>
                    ) : null}
                  </span>
                  <small>{p.why}</small>
                </li>
              ))}
            </ol>
            </details>
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
                      {shortLabel(r.label)}
                      <small>
                        {r.source}, {r.source_date}
                        {by ? ` · included in ${label(by)}` : ""}
                        {r.build_id in calculator ? (
                          <CalculatorNote
                            id={r.build_id}
                            published={r.score}
                            calc={calculator[r.build_id]}
                            model={identities[r.build_id]?.model ?? null}
                          />
                        ) : null}
                      </small>
                    </span>
                    <span className="buildfig">
                      <span className={`fig ${r.score > 0 ? "adds" : "reduces"}`}>{money(r.score)}</span>
                      {identities[r.build_id] ? <EstimateTag identity={identities[r.build_id].published} short /> : null}
                    </span>
                  </label>
                );
              })}
          </fieldset>
        ))}
      </div>
      <PackageSummary
        rows={rows}
        selected={selected}
        identity={packageIdentity}
        philosophy={philosophy}
        notice={notice}
        onUndo={undo}
        onClear={() => setSelected([])}
      />
    </div>
    </>
  );
}

// localStorage can be missing or throw (private windows, blocked site data);
// the package then lives only in the URL, as it did before.
const STORE_KEY = "fpc-package";

function readStored(): string | null {
  try {
    return window.localStorage.getItem(STORE_KEY);
  } catch {
    return null;
  }
}

function writeStored(value: string): void {
  try {
    window.localStorage.setItem(STORE_KEY, value);
  } catch {
    // Nothing to do: the URL still carries the package.
  }
}

function CalculatorNote({
  id,
  published,
  calc,
  model,
}: {
  id: string;
  published: number;
  calc: number;
  model: EstimateIdentity | null;
}) {
  const { share, differs } = calculatorGap(published, calc);
  return (
    <>
      {" · "}
      <a href={`/explore/${id}`} className={differs ? "differs" : undefined}>
        calculator {money(calc)}
      </a>
      {model ? (
        <>
          {" "}
          <EstimateTag identity={model} short />
        </>
      ) : null}
      {differs ? (
        <span className="differs">
          {Number.isFinite(share) && Math.sign(calc) === Math.sign(published)
            ? `, ${Math.round(share * 100)}% ${Math.abs(calc) > Math.abs(published) ? "larger" : "smaller"}`
            : ", opposite sign"}
        </span>
      ) : null}
    </>
  );
}
