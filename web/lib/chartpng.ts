/** The words burned into a downloaded chart. Title, source, vintage, in that order. */

export function pngCaption(title: string, source: string, vintage: string): string[] {
  return [title, `${source}. ${vintage}.`];
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
