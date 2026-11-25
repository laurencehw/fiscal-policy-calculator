// Presets Tailor can score as a rate and a threshold. Each figure is the
// conventional ten-year result of that Tailor request, checked against the
// preset file so a shape that no longer reproduces the export drops out.
import { toQuery, type TailorInput } from "./tailor";

export type TailorShape = TailorInput & { tenYear: number };

export const TAILOR_SHAPES: Record<string, TailorShape> = {
  "top-rate-39-6": { kind: "income", rate: 2.6, who: 400_000, duration: 10, dynamic: false, tenYear: -231.44 },
  "middle-class-rate-cut-2pp": { kind: "income", rate: -2, who: 50_000, duration: 10, dynamic: false, tenYear: 1401.62 },
  "across-the-board-rate-cut-5pp": { kind: "income", rate: -5, who: 0, duration: 10, dynamic: false, tenYear: 6876.73 },
  "top-rate-45": { kind: "income", rate: 8, who: 609_350, duration: 10, dynamic: false, tenYear: -881.86 },
  "corporate-28pct": { kind: "corporate", rate: 7, who: 0, duration: 10, dynamic: false, tenYear: -968.82 },
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

/**
 * The preset a Tailor request reproduces, if any: same kind, rate, threshold and
 * duration (the dynamic switch does not change the policy). Tailor uses it to
 * show the preset's published score instead of saying none is on file.
 */
export function matchingPreset(input: Pick<TailorInput, "kind" | "rate" | "who" | "duration">): string | null {
  for (const [id, shape] of Object.entries(TAILOR_SHAPES)) {
    if (
      shape.kind === input.kind &&
      Math.abs(shape.rate - input.rate) < 1e-9 &&
      shape.who === input.who &&
      shape.duration === input.duration
    ) {
      return id;
    }
  }
  return null;
}
