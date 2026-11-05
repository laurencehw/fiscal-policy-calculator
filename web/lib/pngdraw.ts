// Browser-only: turn SVG markup into a PNG with the title above and the
// estimate's tag below, sized by pngLayout. Kept apart from chartpng.ts so the
// arithmetic there stays testable under node.
import { FOOT_FONT, FOOT_LINE, PNG_PAD, TITLE_FONT, TITLE_LINE, pngLayout, type PngText } from "./chartpng";

/** Inline the computed stroke and fill of a chart on the page, so the PNG keeps its colours. */
export function svgMarkup(svg: SVGSVGElement): { markup: string; width: number; height: number } {
  const box = svg.getBoundingClientRect();
  const width = Math.max(1, Math.round(box.width));
  const height = Math.max(1, Math.round(box.height));
  const clone = svg.cloneNode(true) as SVGSVGElement;
  const source = svg.querySelectorAll("*");
  const copied = clone.querySelectorAll("*");
  source.forEach((node, index) => {
    const style = getComputedStyle(node);
    const element = copied[index] as Element;
    if (style.stroke && style.stroke !== "none") element.setAttribute("stroke", style.stroke);
    if (style.fill && style.fill !== "none") element.setAttribute("fill", style.fill);
  });
  clone.setAttribute("width", String(width));
  clone.setAttribute("height", String(height));
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  return { markup: new XMLSerializer().serializeToString(clone), width, height };
}

export function pageColors(): { ink: string; paper: string } {
  const body = getComputedStyle(document.body);
  return { ink: body.color || "#1b1b1a", paper: body.backgroundColor || "#fbfaf6" };
}

export function renderPng(markup: string, width: number, height: number, text: PngText): Promise<Blob> {
  const url = URL.createObjectURL(new Blob([markup], { type: "image/svg+xml;charset=utf-8" }));
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        URL.revokeObjectURL(url);
        reject(new Error("no canvas"));
        return;
      }
      const measure = (font: string) => (sample: string) => {
        ctx.font = font;
        return ctx.measureText(sample).width;
      };
      const layout = pngLayout(text, width, height, measure(TITLE_FONT), measure(FOOT_FONT));
      canvas.width = width * 2;
      canvas.height = layout.height * 2;
      ctx.scale(2, 2);
      const { ink, paper } = pageColors();
      ctx.fillStyle = paper;
      ctx.fillRect(0, 0, width, layout.height);
      ctx.fillStyle = ink;
      ctx.font = TITLE_FONT;
      layout.titleLines.forEach((line, i) => ctx.fillText(line, PNG_PAD, layout.titleY + i * TITLE_LINE));
      ctx.drawImage(image, 0, layout.header, width, height);
      ctx.font = FOOT_FONT;
      const top = layout.header + height;
      layout.footLines.forEach((line, i) => ctx.fillText(line, PNG_PAD, top + layout.footY + i * FOOT_LINE));
      URL.revokeObjectURL(url);
      canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("empty png"))), "image/png");
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("svg"));
    };
    image.src = url;
  });
}

export function saveBlob(blob: Blob, name: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function copyText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
}
