// Display helpers. Money is in billions of dollars, deficit convention.

/** "+$4,581.9B", "-$302.2B", or "$1.4T" style when asked. Zero prints without a sign. */
export function money(billions: number, opts: { trillions?: boolean } = {}): string {
  const sign = billions > 0 ? "+" : billions < 0 ? "-" : "";
  const abs = Math.abs(billions);
  if (opts.trillions && abs >= 1000) {
    return `${sign}$${(abs / 1000).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}T`;
  }
  return `${sign}$${abs.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}B`;
}

/** What a deficit-convention figure means, in words. */
export function direction(billions: number): string {
  if (billions > 0) return "adds to the deficit";
  if (billions < 0) return "reduces the deficit";
  return "leaves the deficit unchanged";
}

export function pct(value: number, digits = 1): string {
  return `${value.toFixed(digits)}%`;
}

/**
 * Preset labels come from the Streamlit app: a leading emoji, Markdown-escaped
 * dollar signs, and sometimes a quoted figure in brackets. Keep the words.
 */
export function cleanLabel(label: string): string {
  return label
    .replace(/\\\$/g, "$")
    .replace(/^[^\p{L}\p{N}$]+/u, "")
    .trim();
}

/** The same label without its bracketed figure, for headings. */
export function shortLabel(label: string): string {
  return cleanLabel(label).replace(/\s*\([^)]*\$[^)]*\)\s*$/, "").trim();
}

/** Whole dollars with a sign, for per-return amounts: "+$28,273", "-$1,274", "$0". */
export function dollars(value: number): string {
  const rounded = Math.round(value);
  const sign = rounded > 0 ? "+" : rounded < 0 ? "-" : "";
  return `${sign}$${Math.abs(rounded).toLocaleString("en-US")}`;
}
