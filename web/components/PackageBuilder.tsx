"use client";
// Build: tick policies, see the package's ten-year list-price total. State lives
// in ?policies=, the same parameter the Streamlit app's share links use.
import { useEffect, useMemo, useState } from "react";
import { cleanLabel, money } from "@/lib/format";
import { choose, covered, fromQuery, total } from "@/lib/package";
import type { BuildRow } from "@/lib/types";

export function PackageBuilder({ rows, scored }: { rows: BuildRow[]; scored: string[] }) {
  const [selected, setSelected] = useState<string[]>([]);
  const scoredIds = useMemo(() => new Set(scored), [scored]);

  useEffect(() => {
    setSelected(fromQuery(rows, new URLSearchParams(window.location.search).get("policies")));
  }, [rows]);

  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.delete("policies");
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

  return (
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
  );
}
