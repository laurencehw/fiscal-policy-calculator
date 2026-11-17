"use client";

import { money } from "@/lib/format";
import { lawInfo, type LawCatalog, type LawId, type SourcedFigure } from "@/lib/lawBaseline";

function Figure({ figure, label }: { figure: SourcedFigure; label: string }) {
  return (
    <li>
      <b>{label}.</b> {money(figure.billions, { trillions: true })} over {figure.window} ({figure.convention}).{" "}
      <a href={figure.url}>{figure.source}</a>
      {figure.approximated ? " — approximated." : "."}
      {figure.note ? ` ${figure.note}` : ""}
    </li>
  );
}

/** Why the same policy scores differently on each yardstick, with sourced totals. */
export function LawLesson({
  catalog,
  law,
  compact = false,
}: {
  catalog: LawCatalog;
  law: LawId;
  compact?: boolean;
}) {
  const info = lawInfo(catalog, law);
  const figs = catalog.figures;
  const sources = (
    <ul className="marked">
      <Figure
        figure={figs.pl119_21_conventional}
        label="P.L. 119-21 vs pre-2025 law, conventional"
      />
      <Figure
        figure={figs.pl119_21_outlook}
        label="The same law in CBO's February 2026 Outlook, with macro effects and debt service"
      />
      <Figure
        figure={figs.temps_extended_primary}
        label="Extending P.L. 119-21's temporary provisions vs current law"
      />
      <Figure
        figure={figs.house_passed_temps}
        label="CBO's earlier letter on making 16 tax provisions in House-passed H.R. 1 permanent"
      />
    </ul>
  );
  if (compact) {
    return (
      <details className="lawlesson compact" aria-label="Why scores depend on the baseline">
        <summary>Why scores change with the baseline</summary>
        <p className="sentence">{info.lesson}</p>
        <p className="note">{catalog.worked_example}</p>
        {sources}
      </details>
    );
  }
  return (
    <aside className="lawlesson" aria-label="Why scores depend on the baseline">
      <p className="sentence">{info.lesson}</p>
      <p className="note">{catalog.worked_example}</p>
      <details>
        <summary>Where the baseline differences are from</summary>
        {sources}
      </details>
    </aside>
  );
}
