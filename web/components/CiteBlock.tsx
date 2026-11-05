"use client";
// A citation a reader can copy, built from the same identity as the figure's tag.
import { useFlash } from "@/components/ChartActions";
import { copyText } from "@/lib/pngdraw";

export function CiteBlock({ text, label = "Cite as" }: { text: string; label?: string }) {
  const [note, flash] = useFlash();
  return (
    <div className="cite">
      <span className="tag">{label}</span>
      <p className="citetext">{text}</p>
      <button type="button" onClick={() => void copyText(text).then(() => flash("Copied"))}>
        {note || "Copy citation"}
      </button>
      <span className="sr-only" aria-live="polite">
        {note}
      </span>
    </div>
  );
}
