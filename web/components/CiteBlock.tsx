"use client";
// A citation a reader can copy, built from the same identity as the figure's tag,
// plus the same reference as a BibTeX or RIS file for a reference manager.
import { useFlash } from "@/components/ChartActions";
import { copyText, saveBlob } from "@/lib/pngdraw";
import type { Citation } from "@/lib/share";

export function CiteBlock({ cite, label = "Cite as" }: { cite: Citation; label?: string }) {
  const [note, flash] = useFlash();
  function download(body: string, extension: "bib" | "ris", type: string) {
    saveBlob(new Blob([body], { type: `${type};charset=utf-8` }), `${cite.fileStem}.${extension}`);
  }
  return (
    <div className="cite">
      <span className="tag">{label}</span>
      <p className="citetext">{cite.text}</p>
      <p className="citeactions">
        <button type="button" onClick={() => void copyText(cite.text).then(() => flash("Copied"))}>
          {note || "Copy citation"}
        </button>
        <button type="button" onClick={() => download(cite.bibtex, "bib", "application/x-bibtex")}>
          BibTeX
        </button>
        <button type="button" onClick={() => download(cite.ris, "ris", "application/x-research-info-systems")}>
          RIS
        </button>
      </p>
      <span className="sr-only" aria-live="polite">
        {note}
      </span>
    </div>
  );
}
