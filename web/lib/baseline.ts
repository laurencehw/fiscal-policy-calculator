// Draw a proposal on CBO's baseline. Deficit in the file keeps CBO's sign
// (negative is a deficit); every figure this module returns uses the site's
// convention, positive adds to the deficit or to the debt.

export type BaselineYear = {
  fiscal_year: number;
  deficit_billions: number;
  debt_held_by_public_billions: number;
  nominal_gdp_billions: number;
};

export type BaselineFile = {
  vintage: string;
  vintage_label: string;
  window: string;
  years: BaselineYear[];
};

export type Effect = { year: number; value: number };

export type PathPoint = {
  year: number;
  baselineDeficit: number;
  policyDeficit: number;
  baselineDebt: number;
  policyDebt: number;
  gdp: number;
};

/** Current law and the proposal, on the years the score and the baseline share. */
export function deficitPaths(years: BaselineYear[], effects: Effect[]): PathPoint[] {
  const byYear = new Map(effects.map((row) => [row.year, row.value]));
  let cumulative = 0;
  const points: PathPoint[] = [];
  for (const year of years) {
    const effect = byYear.get(year.fiscal_year);
    if (effect === undefined) continue;
    cumulative += effect;
    const baselineDeficit = -year.deficit_billions;
    points.push({
      year: year.fiscal_year,
      baselineDeficit,
      policyDeficit: baselineDeficit + effect,
      baselineDebt: year.debt_held_by_public_billions,
      policyDebt: year.debt_held_by_public_billions + cumulative,
      gdp: year.nominal_gdp_billions,
    });
  }
  return points;
}

export function sum(values: number[]): number {
  return values.reduce((total, value) => total + value, 0);
}

/** The proposal's ten-year effect is the gap between the two deficit paths. */
export function pathGap(points: PathPoint[]): number {
  return sum(points.map((row) => row.policyDeficit)) - sum(points.map((row) => row.baselineDeficit));
}

export function trillions(billions: number): string {
  const sign = billions < 0 ? "-" : "";
  return `${sign}$${(Math.abs(billions) / 1000).toFixed(1)}T`;
}

/** Short axis labels. A $32,095B tick does not fit a phone. */
export function axisMoney(billions: number): string {
  const sign = billions < 0 ? "-" : "";
  const abs = Math.abs(billions);
  if (abs >= 10000) return `${sign}$${Math.round(abs / 1000)}T`;
  if (abs >= 1000) return `${sign}$${(abs / 1000).toFixed(1)}T`;
  return `${sign}$${Math.round(abs)}B`;
}
