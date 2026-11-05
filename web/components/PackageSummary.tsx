"use client";

import { useEffect, useRef } from "react";
import { EstimateTag } from "@/components/EstimateTag";
import { money, shortLabel } from "@/lib/format";
import type { EstimateIdentity } from "@/lib/identity";
import { remainingGap, targetShare } from "@/lib/package";
import type { BuildRow, ValuesArchetype } from "@/lib/types";

/** The package total, its bars, and the replacement notice. Sticky on a desktop, a sheet on a phone. */
export function PackageSummary({
  rows,
  selected,
  identity,
  philosophy,
  notice,
  onUndo,
  onClear,
  secondTotal,
}: {
  rows: BuildRow[];
  selected: string[];
  identity: EstimateIdentity;
  philosophy: ValuesArchetype | null;
  notice: string | null;
  onUndo: () => void;
  onClear: () => void;
  /** Slot for the jointly scored package. Rendered only when a later lane passes it. */
  secondTotal?: number;
}) {
  const noticeRef = useRef<HTMLParagraphElement>(null);
  const sum = rows.filter((row) => selected.includes(row.build_id)).reduce((total, row) => total + row.score, 0);
  const chosen = new Set(selected);
  const picked = rows.filter((row) => chosen.has(row.build_id));
  const scale = Math.max(1, ...picked.map((row) => Math.abs(row.score)));
  const gap = philosophy ? philosophy.gap_billions : null;
  const remaining = gap === null ? null : remainingGap(sum, gap);
  const share = gap === null ? null : targetShare(sum, gap);

  useEffect(() => {
    if (notice) noticeRef.current?.focus();
  }, [notice]);

  return (
    <details className="buildtotal" open>
      <summary>
        <span className={`fig big ${sum > 0 ? "adds" : sum < 0 ? "reduces" : ""}`}>{money(sum)}</span>
        {remaining !== null ? <span className="note">{money(remaining)} still to the target</span> : null}
      </summary>
      {notice ? (
        <p className="note" role="status" tabIndex={-1} ref={noticeRef}>
          {notice}{" "}
          <button type="button" onClick={onUndo}>
            Undo
          </button>
        </p>
      ) : null}
      <div data-package-total>
        <span className="eyebrow">Sum of standalone published scores</span>
        <p className={`fig big ${sum > 0 ? "adds" : sum < 0 ? "reduces" : ""}`}>{money(sum)}</p>
        <EstimateTag identity={identity} />
        <p className="note">Interactions between these policies are not measured.</p>
        {remaining !== null && share !== null ? (
          <p className="note">
            {money(remaining)} left of the {philosophy?.target_pct_gdp.toFixed(1)}% of GDP target, {Math.round(share * 100)}%
            closed.
          </p>
        ) : null}
        {secondTotal !== undefined ? <p className="note">Jointly scored {money(secondTotal)}.</p> : null}
      </div>
      {picked.length ? (
        <ul className="contrib">
          {picked.map((row) => (
            <li key={row.build_id}>
              <span>{shortLabel(row.label)}</span>
              <span className="bartrack" aria-hidden="true">
                <span className={`bar ${row.score > 0 ? "adds" : "reduces"}`} style={{ width: `${(Math.abs(row.score) / scale) * 100}%` }} />
              </span>
              <span className={`fig ${row.score > 0 ? "adds" : "reduces"}`}>{money(row.score)}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="note">Tick policies to add their ten-year figures.</p>
      )}
      {selected.length ? (
        <button type="button" onClick={onClear}>
          Clear
        </button>
      ) : null}
    </details>
  );
}
