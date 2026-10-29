// The Generations page's inputs, shared by the sliders and the /api/olg route.
// Bounds and steps are the Streamlit app's Generational tab; rates are percent
// on the page and fractions on the engine.

export type OlgInput = { capital_tax_rate: number; payroll_tax_rate: number; replacement_rate: number };

export const OLG_SLIDERS = [
  { key: "capital_tax_rate", param: "capital", label: "Capital tax rate", min: 5, max: 60, step: 1, base: 30, help: "Effective tax on capital income, corporate and individual together." },
  { key: "payroll_tax_rate", param: "payroll", label: "Social Security payroll tax", min: 0, max: 20, step: 0.1, base: 12.4, help: "Employee and employer shares together." },
  { key: "replacement_rate", param: "replacement", label: "Social Security replacement rate", min: 0, max: 80, step: 5, base: 40, help: "Benefit as a share of the average wage." },
] as const;

export type OlgKey = (typeof OLG_SLIDERS)[number]["key"];

/** Check a request body; return fractions for the engine, or a reason it was refused. */
export function validateOlg(body: unknown): OlgInput | string {
  if (!body || typeof body !== "object") return "Expected a JSON object.";
  const b = body as Record<string, unknown>;
  const out: Partial<OlgInput> = {};
  for (const s of OLG_SLIDERS) {
    const v = b[s.key];
    if (typeof v !== "number" || !Number.isFinite(v)) return `${s.key} must be a number.`;
    if (v < s.min || v > s.max) return `${s.key} must be between ${s.min} and ${s.max} percent.`;
    out[s.key] = Math.round(v * 1e4) / 1e6;
  }
  return out as OlgInput;
}

/** Percent inputs from a /generations query; a bad or missing value keeps the baseline. */
export function olgFromQuery(params: URLSearchParams): Record<OlgKey, number> {
  const out = {} as Record<OlgKey, number>;
  for (const s of OLG_SLIDERS) {
    const raw = params.get(s.param);
    const n = raw === null || raw.trim() === "" ? NaN : Number(raw);
    out[s.key] = Number.isFinite(n) ? Math.max(s.min, Math.min(s.max, n)) : s.base;
  }
  return out;
}

export function olgToQuery(values: Record<OlgKey, number>): string {
  return OLG_SLIDERS.map((s) => `${s.param}=${values[s.key]}`).join("&");
}
