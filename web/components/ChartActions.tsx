"use client";

import { useEffect, useRef, useState } from "react";
import { pngFileName, pngText } from "@/lib/chartpng";
import { renderPng, saveBlob, svgMarkup, copyText } from "@/lib/pngdraw";
import { withVersion } from "@/lib/share";

/** A short-lived status word on a button: "Copied", then back to the button's own label. */
export function useFlash(ms = 2000): [string, (text: string) => void] {
  const [note, setNote] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);
  function flash(text: string) {
    setNote(text);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setNote(""), ms);
  }
  return [note, flash];
}

/**
 * Download the chart as a PNG with the estimate's long tag under it, and copy
 * the page link stamped with the scores date. No extra dependency.
 */
export function ChartActions({
  chartId,
  title,
  identity,
  site,
  scoresDate,
}: {
  chartId: string;
  title: string;
  /** identityLine(...) of the figure the chart draws. */
  identity: string;
  /** Where the figure comes from, e.g. "fiscal.lwilsesamson.com/explore/x". */
  site: string;
  scoresDate: string;
}) {
  const [linkNote, flashLink] = useFlash();
  const [pngNote, flashPng] = useFlash(4000);
  async function download() {
    try {
      const svg = document.getElementById(chartId)?.querySelector("svg");
      if (!(svg instanceof SVGSVGElement)) throw new Error("no chart");
      const { markup, width, height } = svgMarkup(svg);
      const blob = await renderPng(markup, width, height, pngText(title, identity, site));
      saveBlob(blob, pngFileName(title));
    } catch {
      flashPng("Could not render the chart");
    }
  }
  async function copy() {
    await copyText(withVersion(window.location.href, scoresDate));
    flashLink("Copied");
  }
  return (
    <>
      <button type="button" onClick={() => void download()}>
        {pngNote || "Download PNG"}
      </button>
      <button type="button" onClick={() => void copy()}>
        {linkNote || "Copy link"}
      </button>
      <span className="sr-only" aria-live="polite">
        {pngNote || linkNote}
      </span>
    </>
  );
}
