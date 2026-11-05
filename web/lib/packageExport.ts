// Build's exports: the package as a CSV and as a picture. Both say first what
// the total is (a sum of standalone published scores) and what it leaves out
// (interactions between the policies), because a total copied into a memo
// travels without the page around it.
import { money, shortLabel } from "./format";
import type { BuildRow } from "./types";

/** The sentence every Build export opens with. */
export const PACKAGE_EXCLUSION = "Sum of standalone published scores; interactions between these policies are not measured.";

function cell(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/** The package's rows in catalog order. */
function chosen(rows: BuildRow[], selected: string[]): BuildRow[] {
  const ids = new Set(selected);
  return rows.filter((r) => ids.has(r.build_id));
}

/**
 * The package as CSV. Comment lines first (the exclusion sentence, then the
 * units and where the link lives), then one row per policy and a total row.
 * `calculator` is this calculator's own conventional score where it has one.
 */
export function packageCsv(
  rows: BuildRow[],
  selected: string[],
  calculator: Record<string, number>,
  opts: { link: string; dated: string },
): string {
  const list = chosen(rows, selected);
  const sum = list.reduce((s, r) => s + r.score, 0);
  const lines = [
    `# ${PACKAGE_EXCLUSION}`,
    "# Billions of dollars over ten years, each on its source's own window. Positive increases the deficit, negative reduces it.",
    `# ${opts.dated ? `Figures dated ${opts.dated}. ` : ""}${opts.link}`,
    "build_id,policy,published_ten_year,source,source_date,calculator_conventional_ten_year",
  ];
  for (const r of list) {
    const calc = calculator[r.build_id];
    lines.push(
      [r.build_id, shortLabel(r.label), r.score, r.source, r.source_date, typeof calc === "number" ? Math.round(calc * 10) / 10 : null]
        .map(cell)
        .join(","),
    );
  }
  lines.push(["total", "Sum of the published figures above", Math.round(sum * 10) / 10, "", "", ""].map(cell).join(","));
  return lines.join("\n") + "\n";
}

export type PackageChartColors = { ink: string; muted: string; rule: string; adds: string; reduces: string; paper: string };

function esc(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/**
 * The package's contributions as a self-contained SVG: one row per policy, a
 * bar from a shared zero, the figure, then the total. Colours come in as
 * values, so the drawing does not depend on the page's stylesheet.
 */
export function packageSvg(
  rows: BuildRow[],
  selected: string[],
  width: number,
  colors: PackageChartColors,
): { svg: string; width: number; height: number } {
  const list = chosen(rows, selected);
  const sum = list.reduce((s, r) => s + r.score, 0);
  const scale = Math.max(1, ...list.map((r) => Math.abs(r.score)));
  const rowH = 34;
  const pad = 8;
  const half = (width - 2 * pad) / 2;
  const mid = pad + half;
  const parts: string[] = [];
  list.forEach((r, i) => {
    const y = pad + i * rowH;
    const w = (Math.abs(r.score) / scale) * half;
    const x = r.score > 0 ? mid : mid - w;
    const color = r.score > 0 ? colors.adds : colors.reduces;
    parts.push(
      `<text x="${pad}" y="${y + 12}" font-family="sans-serif" font-size="12" fill="${colors.ink}">${esc(shortLabel(r.label))}</text>`,
      `<text x="${width - pad}" y="${y + 12}" text-anchor="end" font-family="sans-serif" font-size="12" fill="${color}">${esc(money(r.score))}</text>`,
      `<rect x="${x.toFixed(1)}" y="${y + 18}" width="${Math.max(1, w).toFixed(1)}" height="8" fill="${color}"/>`,
    );
  });
  const axisBottom = pad + list.length * rowH;
  parts.push(`<line x1="${mid}" y1="${pad}" x2="${mid}" y2="${axisBottom}" stroke="${colors.rule}" stroke-width="1"/>`);
  const totalY = axisBottom + 22;
  parts.push(
    `<line x1="${pad}" y1="${axisBottom + 4}" x2="${width - pad}" y2="${axisBottom + 4}" stroke="${colors.ink}" stroke-width="1"/>`,
    `<text x="${pad}" y="${totalY}" font-family="Georgia, serif" font-size="15" fill="${colors.ink}">Package total</text>`,
    `<text x="${width - pad}" y="${totalY}" text-anchor="end" font-family="Georgia, serif" font-size="15" fill="${sum > 0 ? colors.adds : colors.reduces}">${esc(money(sum))}</text>`,
  );
  const height = totalY + pad;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="${width}" height="${height}" fill="${colors.paper}"/>${parts.join("")}</svg>`;
  return { svg, width, height };
}
