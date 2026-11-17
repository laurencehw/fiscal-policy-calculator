"use client";

import type { LawCatalog, LawId } from "@/lib/lawBaseline";

/** Segmented control for the three current-law yardsticks. */
export function LawSwitch({
  catalog,
  value,
  onChange,
}: {
  catalog: LawCatalog;
  value: LawId;
  onChange: (law: LawId) => void;
}) {
  return (
    <div className="lawswitch">
      <span className="tag">Measured against</span>
      <div className="seg" role="radiogroup" aria-label="Current-law yardstick">
        {catalog.laws.map((row) => (
          <button
            key={row.id}
            type="button"
            role="radio"
            aria-checked={value === row.id}
            aria-pressed={value === row.id}
            title={row.summary}
            onClick={() => onChange(row.id)}
          >
            {row.short_label}
          </button>
        ))}
      </div>
    </div>
  );
}
