import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

function channel(hex: string, shift: number): number {
  const raw = parseInt(hex.slice(1 + shift, 3 + shift), 16) / 255;
  return raw <= 0.04045 ? raw / 12.92 : ((raw + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  return 0.2126 * channel(hex, 0) + 0.7152 * channel(hex, 2) + 0.0722 * channel(hex, 4);
}

export function contrast(a: string, b: string): number {
  const hi = Math.max(luminance(a), luminance(b));
  const lo = Math.min(luminance(a), luminance(b));
  return (hi + 0.05) / (lo + 0.05);
}

/** Light-mode tokens, the :root block before any prefers-color-scheme override. */
function lightTokens(css: string): { paper: string; s2: string } {
  const root = css.split("@media")[0];
  const paper = root.match(/--paper:\s*(#[0-9a-fA-F]{6})/)?.[1];
  const s2 = root.match(/--s2:\s*(#[0-9a-fA-F]{6})/)?.[1];
  assert.ok(paper && s2, "light-mode --paper and --s2");
  return { paper, s2 };
}

test("the light-mode rust clears 4.5:1 on the paper at figure size", () => {
  const css = fs.readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");
  const { paper, s2 } = lightTokens(css);
  const ratio = contrast(s2, paper);
  assert.ok(ratio >= 4.5, `${s2} on ${paper} is ${ratio.toFixed(2)}:1`);
  assert.equal(paper.toLowerCase(), "#fbfaf6");
  // The previous token was 4.36:1. Dark mode keeps its own rust.
  const dark = css.split("@media")[1] ?? "";
  assert.match(dark, /--s2:\s*#ef8a62/i);
});
