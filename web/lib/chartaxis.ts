// Axis ticks for bar charts, whose bars are lengths measured from zero.

/** Round tick marks for an axis that runs from zero (or below it) to the data's far end. */
export function zeroAxis(values: number[], target = 4): { ticks: number[] } {
  const lo = Math.min(0, ...values);
  const hi = Math.max(0, ...values);
  const span = hi - lo || 1;
  const raw = span / target;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = ([1, 2, 2.5, 5, 10].find((m) => m * mag >= raw) ?? 10) * mag;
  const start = Math.floor(lo / step) * step;
  const ticks: number[] = [];
  for (let t = start; t <= hi + step * 1e-9; t += step) ticks.push(Math.round(t / step) * step);
  if (ticks[ticks.length - 1] < hi) ticks.push(ticks[ticks.length - 1] + step);
  return { ticks };
}

/** Annual deficit effect, one bar per fiscal year; colour says which way it moves the deficit. */
