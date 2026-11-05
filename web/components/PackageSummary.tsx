"use client";
// Build's summary panel: the package's policies on one scale, the total with the
// sentence that says what it leaves out, and the philosophy's target. Sticky
// beside the list on a wide screen; a bottom sheet on a phone, where the total
// and the remaining gap stay in view and the policy list opens on demand.
import { forwardRef, useState } from "react";
import { EstimateTag } from "@/components/EstimateTag";
import { money, shortLabel } from "@/lib/format";
import type { EstimateIdentity } from "@/lib/identity";
import { contributions, towardTarget } from "@/lib/package";
import type { BuildRow } from "@/lib/types";

export type SummaryTarget = { name: string; gapBillions: number; pctGdp: number };

/** Reserved for C6: a jointly scored total beside the sum. Rendered only when given. */
export type SecondTotal = { label: string; value: number; identity?: EstimateIdentity };

type Props = {
  rows: BuildRow[];
  selected: string[];
  sum: number;
  packageIdentity: EstimateIdentity;
  target: SummaryTarget | null;
  notice: string | null;
  canUndo: boolean;
  onUndo: () => void;
  onClear: () => void;
  secondTotal?: SecondTotal | null;
};

export const PackageSummary = forwardRef<HTMLParagraphElement, Props>(function PackageSummary(
  { rows, selected, sum, packageIdentity, target, notice, canUndo, onUndo, onClear, secondTotal },
  noticeRef,
) {
  const [open, setOpen] = useState(false);
  const { rows: list, scale } = contributions(rows, selected);
  const progress = target ? towardTarget(sum, target.gapBillions) : null;
  return (
    <aside className={`buildtotal summary${open ? " open" : ""}`} aria-label="Your package">
      <div className="summarynotice" aria-live="polite">
        {notice ? (
          <p className="note" ref={noticeRef} tabIndex={-1}>
            {notice}{" "}
            {canUndo ? (
              <button type="button" className="undo" onClick={onUndo}>
                Undo
              </button>
            ) : null}
          </p>
        ) : null}
      </div>

      <div className="summarytotal">
        <span className="eyebrow">Your package</span>
        <p className={`fig big ${sum > 0 ? "adds" : sum < 0 ? "reduces" : ""}`}>{money(sum)}</p>
        <EstimateTag identity={packageIdentity} />
        <p className="note exclusion">Interactions between these policies are not measured.</p>
        {secondTotal ? (
          <p className="secondtotal">
            <span className="eyebrow">{secondTotal.label}</span>{" "}
            <span className={`fig ${secondTotal.value > 0 ? "adds" : "reduces"}`}>{money(secondTotal.value)}</span>
            {secondTotal.identity ? <EstimateTag identity={secondTotal.identity} /> : null}
          </p>
        ) : null}
      </div>

      {target && progress ? (
        <p className="note summarytarget">
          {target.name} target, a deficit of {target.pctGdp.toFixed(1)}% of GDP: needs{" "}
          {money(target.gapBillions).replace("+", "")}.{" "}
          {progress.remaining > 0
            ? `${money(progress.remaining).replace("+", "")} left to find (${Math.round(progress.share * 100)}% of the way).`
            : `This package reaches it (${Math.round(progress.share * 100)}% of the way).`}
        </p>
      ) : null}

      {selected.length ? (
        <>
          <button
            type="button"
            className="sheettoggle"
            aria-expanded={open}
            aria-controls="summary-list"
            onClick={() => setOpen((v) => !v)}
          >
            {open ? "Hide" : "Show"} {selected.length} {selected.length === 1 ? "policy" : "policies"}
          </button>
          <ul className="summarylist" id="summary-list">
            {list.map((r) => (
              <li key={r.build_id}>
                <span className="summaryname">{shortLabel(r.label)}</span>
                <span className={`fig ${r.score > 0 ? "adds" : "reduces"}`}>{money(r.score)}</span>
                <span className="summarybar" aria-hidden="true">
                  <span
                    className={r.score > 0 ? "adds" : "reduces"}
                    style={{
                      width: `${(Math.abs(r.score) / scale) * 50}%`,
                      [r.score > 0 ? "left" : "right"]: "50%",
                    }}
                  />
                </span>
              </li>
            ))}
          </ul>
          <button type="button" className="clear" onClick={onClear}>
            Clear
          </button>
        </>
      ) : (
        <p className="note">Tick policies to add their ten-year figures.</p>
      )}
    </aside>
  );
});
