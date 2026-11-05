"use client";
// Build: tick policies, see the package's ten-year list-price total. State lives
// in ?policies=, the same parameter the Streamlit app's share links use.
import { useEffect, useRef, useState } from "react";
import { PackageSummary, type SecondTotal } from "@/components/PackageSummary";
import { EstimateTag } from "@/components/EstimateTag";
import { cleanLabel, money, shortLabel } from "@/lib/format";
import type { EstimateIdentity } from "@/lib/identity";
import { addToPackage, calculatorGap, covered, fromQuery, total, towardTarget, undoReplacement, type Replacement } from "@/lib/package";
import type { BuildRow, ValuesArchetype } from "@/lib/types";
import { CiteBlock } from "@/components/CiteBlock";
import { useFlash } from "@/components/ChartActions";
import { pngText } from "@/lib/chartpng";
import { identityLine } from "@/lib/identity";
import { PACKAGE_EXCLUSION, packageCsv, packageSvg } from "@/lib/packageExport";
import { copyText, renderPng, saveBlob } from "@/lib/pngdraw";
import { citation, longDate, withVersion } from "@/lib/share";

export function PackageBuilder({
  rows,
  calculator,
  identities,
  packageIdentity,
  archetypes = [],
  secondTotal = null,
  scoresDate = "",
  site = "",
}: {
  rows: BuildRow[];
  /** The calculator's ten-year conventional score by build id, where it scores the policy. */
  calculator: Record<string, number>;
  identities: Record<string, { published: EstimateIdentity; model: EstimateIdentity | null }>;
  packageIdentity: EstimateIdentity;
  archetypes?: ValuesArchetype[];
  /** C6's jointly scored total; the summary shows it only when present. */
  secondTotal?: SecondTotal | null;
  /** manifest.json's scores_date, stamped on every link this page hands out as v=. */
  scoresDate?: string;
  /** The site origin, for the citation and the exports. */
  site?: string;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [philosophy, setPhilosophy] = useState<ValuesArchetype | null>(null);
  const [ready, setReady] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [change, setChange] = useState<Replacement | null>(null);
  const noticeRef = useRef<HTMLParagraphElement>(null);
  const nameOf = (policyId: string) => shortLabel(rows.find((r) => r.build_id === policyId)?.label ?? policyId);

  /** The sentence for a tick that pushed policies out: alternatives swap, a broader policy contains. */
  function replacementNotice(r: Replacement): string {
    const row = rows.find((x) => x.build_id === r.added);
    const names = r.dropped.map(nameOf).join(" and ");
    if (row && r.dropped.every((id) => row.subsumes.includes(id))) {
      return `${nameOf(r.added)} includes ${names}, so ${r.dropped.length === 1 ? "it was" : "they were"} taken out.`;
    }
    return `Replaced ${names} with ${nameOf(r.added)}; these are alternatives.`;
  }

  function announce(r: Replacement | null) {
    setChange(r);
    setNotice(r ? replacementNotice(r) : null);
  }

  // Focus follows a replacement notice, so a keyboard or screen-reader user hears it and can reach Undo.
  useEffect(() => {
    if (change) noticeRef.current?.focus();
  }, [change]);

  function usePhilosophy(a: ValuesArchetype) {
    setPhilosophy(a);
    setSelected(fromQuery(rows, a.picks.map((p) => p.policy_id).join(",")));
    announce(null);
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
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
        if (result.replaced.length) announce({ added: add, dropped: result.replaced });
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
    let query = [rest, selected.length ? `policies=${selected.join(",")}` : ""].filter(Boolean).join("&");
    if (scoresDate) query = withVersion(`?${query}`, scoresDate).slice(1);
    window.history.replaceState(null, "", `${url.pathname}${query ? `?${query}` : ""}${url.hash}`);
  }, [selected, ready, scoresDate]);

  const inside = covered(rows, selected);
  const sum = total(rows, selected);
  const areas = [...new Set(rows.map((r) => r.area))];
  const label = (id: string) => cleanLabel(rows.find((r) => r.build_id === id)?.label ?? id);

  function toggle(id: string) {
    if (selected.includes(id)) {
      setSelected(selected.filter((x) => x !== id));
      announce(null);
      return;
    }
    const result = addToPackage(rows, selected, id);
    setSelected(result.selected);
    announce(result.replaced.length ? { added: id, dropped: result.replaced } : null);
  }

  function undo() {
    if (!change) return;
    setSelected(undoReplacement(rows, selected, change));
    setChange(null);
    setNotice(`Put back ${change.dropped.map(nameOf).join(" and ")}.`);
  }

  function clear() {
    setSelected([]);
    announce(null);
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
          <div className="whys" aria-live="polite">
            <p className="shortresult">
              <b>{philosophy.name}:</b> {philosophy.picks.length} {philosophy.picks.length === 1 ? "policy" : "policies"},{" "}
              {Math.round(towardTarget(philosophy.total_billions, philosophy.gap_billions).share * 100)}% of the target.
              {edited ? " You have since edited the list below." : ""}
            </p>
            <details>
              <summary>Why these choices?</summary>
              <p>
                {philosophy.summary}. The package scores {money(philosophy.total_billions)} against a gap of{" "}
                {money(philosophy.gap_billions).replace("+", "")} to a deficit of {philosophy.target_pct_gdp.toFixed(1)}%
                of GDP.
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
        ref={noticeRef}
        rows={rows}
        selected={selected}
        sum={sum}
        packageIdentity={packageIdentity}
        target={
          philosophy
            ? { name: philosophy.name, gapBillions: philosophy.gap_billions, pctGdp: philosophy.target_pct_gdp }
            : null
        }
        notice={notice}
        canUndo={change !== null}
        onUndo={undo}
        onClear={clear}
        secondTotal={secondTotal}
      />
    </div>
    {selected.length ? (
      <PackageExports
        rows={rows}
        selected={selected}
        calculator={calculator}
        packageIdentity={packageIdentity}
        scoresDate={scoresDate}
        site={site}
      />
    ) : null}
    </>
  );
}

/** The package as a CSV, a PNG and a citation, each opening with what the total leaves out. */
function PackageExports({
  rows,
  selected,
  calculator,
  packageIdentity,
  scoresDate,
  site,
}: {
  rows: BuildRow[];
  selected: string[];
  calculator: Record<string, number>;
  packageIdentity: EstimateIdentity;
  scoresDate: string;
  site: string;
}) {
  const [pngNote, flashPng] = useFlash(4000);
  const [linkNote, flashLink] = useFlash();
  const path = `/build?policies=${selected.join(",")}`;
  const link = withVersion(`${site}${path}`, scoresDate);
  const title = `A package of ${selected.length} ${selected.length === 1 ? "policy" : "policies"}`;
  const cite = citation({ title, identity: packageIdentity, path, scoresDate, site });
  const stem = `package-${selected.length}`;

  function downloadCsv() {
    const text = packageCsv(rows, selected, calculator, { link, dated: scoresDate ? longDate(scoresDate) : "" });
    saveBlob(new Blob([text], { type: "text/csv;charset=utf-8" }), `${stem}.csv`);
  }

  async function downloadPng() {
    try {
      const style = getComputedStyle(document.documentElement);
      const read = (name: string, fallback: string) => style.getPropertyValue(name).trim() || fallback;
      const width = 640;
      const { svg, height } = packageSvg(rows, selected, width, {
        ink: read("--ink", "#1b1b1a"),
        muted: read("--muted", "#5f5c55"),
        rule: read("--rule", "#dcd9d0"),
        adds: read("--s2", "#b14c28"),
        reduces: read("--s1", "#1f5e7a"),
        paper: read("--paper", "#fbfaf6"),
      });
      const host = site.replace(/^https?:\/\//, "");
      const blob = await renderPng(svg, width, height, pngText(title, identityLine(packageIdentity), `Fiscal Policy Calculator, ${host}/build`, "Interactions between these policies are not measured."));
      saveBlob(blob, `${stem}.png`);
    } catch {
      flashPng("Could not render the chart");
    }
  }

  return (
    <section className="packageexports" id="exports" aria-labelledby="exports-head">
      <h2 id="exports-head">Take the package with you</h2>
      <p className="note">{PACKAGE_EXCLUSION} The CSV and the picture both open with that sentence.</p>
      <p className="foot">
        <button type="button" onClick={downloadCsv}>
          Download CSV
        </button>
        <button type="button" onClick={() => void downloadPng()}>
          {pngNote || "Download PNG"}
        </button>
        <button type="button" onClick={() => void copyText(link).then(() => flashLink("Copied"))}>
          {linkNote || "Copy link"}
        </button>
        <span className="sr-only" aria-live="polite">
          {pngNote || linkNote}
        </span>
      </p>
      <CiteBlock text={cite.text} />
    </section>
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
