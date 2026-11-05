// The words burned into a downloaded chart, and where they go. The title sits
// above the chart; the footer below it is the estimate's long tag (producer,
// kind, window, baseline, tier), so a PNG pasted into a slide still says what
// the figure is. Pure, so the arithmetic is tested without a canvas.

export const PNG_PAD = 8;
export const TITLE_FONT = "15px Georgia, serif";
export const TITLE_LINE = 18;
export const FOOT_FONT = "12px sans-serif";
export const FOOT_LINE = 16;

export type PngText = { title: string; footer: string[] };

/**
 * The title, and a footer of the estimate's long tag plus where it came from.
 * `identity` is `identityLine(...)`; `caveat` is any sentence the figure needs
 * beside it (Build's "interactions are not measured").
 */
export function pngText(title: string, identity: string, site: string, caveat = ""): PngText {
  const footer = [identity.trim(), caveat.trim(), site.trim()].filter((line) => line.length > 0);
  return { title: title.trim(), footer };
}

/** Wrap on spaces using a caller-supplied width measure, so the test needs no canvas. */
export function wrapText(text: string, maxWidth: number, measure: (sample: string) => number): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let line = "";
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (line && measure(next) > maxWidth) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines;
}

export type PngLayout = {
  titleLines: string[];
  footLines: string[];
  /** Height above the chart: the wrapped title and its padding. */
  header: number;
  /** Height below the chart: the wrapped footer and its padding. */
  footer: number;
  /** Baseline y of the first title line, and of the first footer line relative to the chart's bottom. */
  titleY: number;
  footY: number;
  height: number;
};

/**
 * Wrap first, then size: the header and footer come from the number of wrapped
 * lines, so a long title on a phone-width chart pushes the chart down instead
 * of being drawn over it.
 */
export function pngLayout(
  text: PngText,
  width: number,
  chartHeight: number,
  measureTitle: (sample: string) => number,
  measureFoot: (sample: string) => number,
): PngLayout {
  const inner = Math.max(1, width - 2 * PNG_PAD);
  const titleLines = text.title ? wrapText(text.title, inner, measureTitle) : [];
  const footLines = text.footer.flatMap((line) => wrapText(line, inner, measureFoot));
  const header = titleLines.length ? 2 * PNG_PAD + titleLines.length * TITLE_LINE : PNG_PAD;
  const footer = footLines.length ? 2 * PNG_PAD + footLines.length * FOOT_LINE : PNG_PAD;
  return {
    titleLines,
    footLines,
    header,
    footer,
    titleY: PNG_PAD + TITLE_LINE - 4,
    footY: PNG_PAD + FOOT_LINE - 4,
    height: header + chartHeight + footer,
  };
}

/** A file name from the title: lower case, hyphens, never empty. */
export function pngFileName(title: string, extension = "png"): string {
  const stem = title
    .replace(/[^\w]+/g, "-")
    .replace(/^-|-$/g, "")
    .toLowerCase();
  return `${stem || "chart"}.${extension}`;
}
