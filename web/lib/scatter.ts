/**
 * Geometry for the out-of-sample scatter on /methods (plan C3): model against
 * published on log scales, the 45-degree line and the ±15% / ±25% bands.
 * Pure functions so the band edges can be tested without rendering.
 */
import type { OutOfSampleRow } from "./types";

export type ScatterFrame = { width: number; height: number; left: number; right: number; top: number; bottom: number };

export const FRAME: ScatterFrame = { width: 560, height: 440, left: 56, right: 16, top: 12, bottom: 44 };

/** Tax classes are circles in the six series colours; the two spending classes are squares. */
export const CLASS_STYLE: Record<string, { color: string; shape: "circle" | "square"; hollow?: boolean }> = {
  ordinary_rate_change: { color: "var(--s1)", shape: "circle" },
  corporate: { color: "var(--s2)", shape: "circle" },
  payroll: { color: "var(--s3)", shape: "circle" },
  capital_gains: { color: "var(--s4)", shape: "circle" },
  agi_inclusive_surtax: { color: "var(--s5)", shape: "circle" },
  tax_expenditure: { color: "var(--s6)", shape: "circle" },
  discretionary_spending: { color: "var(--ink)", shape: "square" },
  enacted_law_spending: { color: "var(--ink)", shape: "square", hollow: true },
};

/** Powers of ten that bracket every magnitude in the rows. */
export function domain(rows: OutOfSampleRow[]): [number, number] {
  const mags = rows.flatMap((r) => [Math.abs(r.model), Math.abs(r.published)]).filter((v) => v > 0);
  const lo = 10 ** Math.floor(Math.log10(Math.min(...mags)));
  const hi = 10 ** Math.ceil(Math.log10(Math.max(...mags)));
  return [lo, hi];
}

export function scaler(dom: [number, number], frame: ScatterFrame = FRAME) {
  const [lo, hi] = dom.map(Math.log10);
  const w = frame.width - frame.left - frame.right;
  const h = frame.height - frame.top - frame.bottom;
  return {
    x: (v: number) => frame.left + ((Math.log10(v) - lo) / (hi - lo)) * w,
    y: (v: number) => frame.top + h - ((Math.log10(v) - lo) / (hi - lo)) * h,
  };
}

/** A band of model = published × (1 ± pct), as a closed polygon across the domain. */
export function bandPolygon(dom: [number, number], pct: number, frame: ScatterFrame = FRAME): string {
  const s = scaler(dom, frame);
  const [lo, hi] = dom;
  const pts = [
    [lo, lo * (1 - pct)],
    [hi, hi * (1 - pct)],
    [hi, hi * (1 + pct)],
    [lo, lo * (1 + pct)],
  ];
  return pts.map(([p, m]) => `${s.x(p).toFixed(1)},${s.y(m).toFixed(1)}`).join(" ");
}

export type ScatterPoint = OutOfSampleRow & { cx: number; cy: number; signMismatch: boolean };

export function points(rows: OutOfSampleRow[], dom: [number, number], frame: ScatterFrame = FRAME): ScatterPoint[] {
  const s = scaler(dom, frame);
  return rows.map((r) => ({
    ...r,
    cx: s.x(Math.abs(r.published)),
    cy: s.y(Math.abs(r.model)),
    signMismatch: Math.sign(r.model) !== Math.sign(r.published),
  }));
}

/** Tick values: each power of ten in the domain. */
export function ticks(dom: [number, number]): number[] {
  const out: number[] = [];
  for (let v = dom[0]; v <= dom[1] * 1.0001; v *= 10) out.push(Math.round(v));
  return out;
}
