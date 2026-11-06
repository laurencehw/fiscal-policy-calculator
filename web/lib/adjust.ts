// Presets Tailor can score as a rate and a threshold. Each figure is the
// conventional ten-year result of that Tailor request, checked against the
// preset file so a shape that no longer reproduces the export drops out.
import { toQuery, type TailorInput } from "./tailor";

export type TailorShape = TailorInput & { tenYear: number };

export const TAILOR_SHAPES: Record<string, TailorShape> = {
  "top-rate-39-6": { kind: "income", rate: 2.6, who: 400_000, duration: 10, dynamic: false, tenYear: -309.76 },
  "middle-class-rate-cut-2pp": { kind: "income", rate: -2, who: 50_000, duration: 10, dynamic: false, tenYear: 1473.2 },
  "across-the-board-rate-cut-5pp": { kind: "income", rate: -5, who: 0, duration: 10, dynamic: false, tenYear: 6585.02 },
  "top-rate-45": { kind: "income", rate: 8, who: 609_350, duration: 10, dynamic: false, tenYear: -1036.66 },
  "corporate-28pct": { kind: "corporate", rate: 7, who: 0, duration: 10, dynamic: false, tenYear: -1310.92 },
};

/** True when Tailor's rate form reproduces this preset's ten-year figure. */
export function adjustable(presetId: string): boolean {
  return Object.prototype.hasOwnProperty.call(TAILOR_SHAPES, presetId);
}

export function tailorHref(presetId: string): string | null {
  const shape = TAILOR_SHAPES[presetId];
  if (!shape) return null;
  const { tenYear: _tenYear, ...input } = shape;
  return `/tailor?${toQuery(input)}`;
}
