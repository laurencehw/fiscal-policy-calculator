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

/** The calculator's one-window total beside the sum (bet 4). Rendered only when given. */
export type SecondTotal = { label: string; value: number; notes: string[]; identity?: EstimateIdentity };

/**
 * Which total leads. The calculator's own total, on one window and one baseline
 * with the measured overlap applied, leads when it scores every ticked policy.
 * When it leaves one out, the published list-price sum leads, since it is the
 * only figure that covers the whole package (outside review, 23 Nov 2026).
 */
export function calculatorLeads(secondTotal: SecondTotal | null | undefined, covers: boolean): boolean {
  return Boolean(secondTotal) && covers;
}

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
  /** True when the calculator scores every ticked policy, so its total leads. */
  calculatorCovers?: boolean;
  /** How the ticked policies interact, one sentence per finding; empty under two policies. */
  interactions?: string[];
};

export const PackageSummary = forwardRef<HTMLParagraphElement, Props>(function PackageSummary(
  {
    rows,
    selected,
    sum,
    packageIdentity,
    target,
    notice,
    canUndo,
    onUndo,
    onClear,
    secondTotal,
    calculatorCovers = false,
    interactions = [],
  },
  noticeRef,
) {
  const [open, setOpen] = useState(false);
  const { rows: list, scale } = contributions(rows, selected);
  const progress = target ? towardTarget(sum, target.gapBillions) : null;
  const leads = calculatorLeads(secondTotal, calculatorCovers);
  return (
    <aside className={`buildtotal summary${open ? " open" : ""}`} aria-label="Your package" id="your-package" tabIndex={-1}>
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
        {leads && secondTotal ? (
          <>
            <span className="eyebrow">Your package, {secondTotal.label.replace(/^Calculator total/, "calculator total")}</span>
            <p className={`fig big ${secondTotal.value > 0 ? "adds" : secondTotal.value < 0 ? "reduces" : ""}`}>
              {money(secondTotal.value)}
            </p>
            {secondTotal.identity ? <EstimateTag identity={secondTotal.identity} /> : null}
            {secondTotal.notes.map((n) => (
              <p className="note summarynote" key={n}>
                {n}
              </p>
            ))}
            <div className="secondtotal">
              <p>
                <span className="eyebrow">Sum of published list prices</span>{" "}
                <span className={`fig ${sum > 0 ? "adds" : sum < 0 ? "reduces" : ""}`}>{money(sum)}</span>
              </p>
              <EstimateTag identity={packageIdentity} />
            </div>
          </>
        ) : (
          <>
        <span className="eyebrow">Your package</span>
        <p className={`fig big ${sum > 0 ? "adds" : sum < 0 ? "reduces" : ""}`}>{money(sum)}</p>
        <EstimateTag identity={packageIdentity} />
        {secondTotal ? (
          <div className="secondtotal">
            <p>
              <span className="eyebrow">{secondTotal.label}</span>{" "}
              <span className={`fig ${secondTotal.value > 0 ? "adds" : secondTotal.value < 0 ? "reduces" : ""}`}>
                {money(secondTotal.value)}
              </span>
            </p>
            {secondTotal.identity ? <EstimateTag identity={secondTotal.identity} /> : null}
            {secondTotal.notes.map((n) => (
              <p className="note summarynote" key={n}>
                {n}
              </p>
            ))}
          </div>
        ) : null}
          </>
        )}
        {interactions.map((n) => (
          <p className="note exclusion summarynote" key={n}>
            {n}
          </p>
        ))}
      </div>

      {target && progress ? (
        <p className="note summarytarget">
          {target.name} target, a deficit of {target.pctGdp.toFixed(1)}% of GDP: needs{" "}
          {money(target.gapBillions).replace("+", "")}
          {leads ? ", measured on the published list prices" : ""}.{" "}
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
            {secondTotal || interactions.length ? " and notes" : ""}
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
