"use client";

import { useState } from "react";
import { pngCaption, wrapText } from "@/lib/chartpng";

function paint(svg: SVGSVGElement, lines: string[]): Promise<Blob> {
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
  const xml = new XMLSerializer().serializeToString(clone);
  const url = URL.createObjectURL(new Blob([xml], { type: "image/svg+xml;charset=utf-8" }));
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => {
      const header = 28 + lines.length * 18;
      const canvas = document.createElement("canvas");
      canvas.width = width * 2;
      canvas.height = (height + header) * 2;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        URL.revokeObjectURL(url);
        reject(new Error("no canvas"));
        return;
      }
      ctx.scale(2, 2);
      const ink = getComputedStyle(document.body).color || "#1b1b1a";
      const paper = getComputedStyle(document.body).backgroundColor || "#fbfaf6";
      ctx.fillStyle = paper;
      ctx.fillRect(0, 0, width, height + header);
      ctx.fillStyle = ink;
      ctx.font = "15px Georgia, serif";
      let y = 20;
      for (const line of wrapText(lines[0] ?? "", width - 16, (sample) => ctx.measureText(sample).width)) {
        ctx.fillText(line, 8, y);
        y += 18;
      }
      ctx.font = "12px sans-serif";
      for (const line of wrapText(lines.slice(1).join(" "), width - 16, (sample) => ctx.measureText(sample).width)) {
        ctx.fillText(line, 8, y);
        y += 16;
      }
      ctx.drawImage(image, 0, header);
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

/** Download the chart as a PNG, and copy the page link. No extra dependency. */
export function ChartActions({
  chartId,
  title,
  source,
  vintage,
}: {
  chartId: string;
  title: string;
  source: string;
  vintage: string;
}) {
  const [note, setNote] = useState("");
  async function download() {
    const svg = document.getElementById(chartId)?.querySelector("svg");
    if (!(svg instanceof SVGSVGElement)) return;
    const blob = await paint(svg, pngCaption(title, source, vintage));
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${title.replace(/[^\w]+/g, "-").replace(/^-|-$/g, "").toLowerCase() || "chart"}.png`;
    link.click();
    URL.revokeObjectURL(url);
  }
  async function copy() {
    const url = window.location.href;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      const area = document.createElement("textarea");
      area.value = url;
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    setNote("Copied");
  }
  return (
    <>
      <button type="button" onClick={() => void download()}>
        Download PNG
      </button>
      <button type="button" onClick={() => void copy()}>
        {note || "Copy link"}
      </button>
    </>
  );
}
