// Place each house, the model, and an optional published range on one line.

export type HouseEstimate = {
  estimator: string;
  document: string;
  value_billions: number;
  fitted: boolean;
};

export type HouseRange = {
  low_billions: number;
  high_billions: number;
  source_name: string;
  source_document: string;
  label: string;
};

export type HouseStripData = {
  policy_id: string;
  model_billions: number;
  subject: string;
  window: string;
  basis: string;
  caveat: string;
  estimates: HouseEstimate[];
  range: HouseRange | null;
};

export type Mark = { key: string; left: number; value: number; kind: "house" | "model" | "range"; label: string; fitted?: boolean };

/** Percent positions, inset so a dot on the end is not clipped. */
export function stripMarks(strip: HouseStripData): { marks: Mark[]; range: { left: number; width: number } | null } {
  const values = [
    strip.model_billions,
    ...strip.estimates.map((row) => row.value_billions),
    ...(strip.range ? [strip.range.low_billions, strip.range.high_billions] : []),
  ];
  const low = Math.min(...values);
  const high = Math.max(...values);
  const span = high - low || 1;
  const place = (value: number) => 6 + ((value - low) / span) * 88;
  const marks: Mark[] = [
    ...strip.estimates.map((row) => ({
      key: row.estimator,
      left: place(row.value_billions),
      value: row.value_billions,
      kind: "house" as const,
      label: row.estimator,
      fitted: row.fitted,
    })),
    {
      key: "model",
      left: place(strip.model_billions),
      value: strip.model_billions,
      kind: "model",
      label: "This calculator",
    },
  ];
  const range = strip.range
    ? { left: place(strip.range.low_billions), width: place(strip.range.high_billions) - place(strip.range.low_billions) }
    : null;
  return { marks, range };
}
