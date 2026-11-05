// One small multiple on the Compare page: the annual conventional deficit
// effect, drawn as plain SVG on the server so it shows with JavaScript off.
// Every multiple on the page gets the same `lo`/`hi`, so equal heights are
// equal dollars.
import type { CompareYear } from "@/lib/compare";
import { money } from "@/lib/format";

const W = 320;
const H = 168;
const LEFT = 52;
const RIGHT = 6;
const TOP = 8;
const BOTTOM = 22;

function tickText(v: number): string {
  return `${v < 0 ? "-" : ""}$${Math.abs(v).toLocaleString("en-US")}B`;
}

export function CompareChart({
  years,
  lo,
  hi,
  ticks,
  label,
}: {
  years: CompareYear[];
  lo: number;
  hi: number;
  ticks: number[];
  label: string;
}) {
  const plotW = W - LEFT - RIGHT;
  const plotH = H - TOP - BOTTOM;
  const span = hi - lo || 1;
  const y = (v: number) => TOP + ((hi - v) / span) * plotH;
  const slot = plotW / Math.max(1, years.length);
  const barW = Math.min(22, slot * 0.72);
  const first = years[0]?.year;
  const last = years[years.length - 1]?.year;
  return (
    <svg className="smallmultiple" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={LEFT} x2={W - RIGHT} y1={y(t)} y2={y(t)} stroke={t === 0 ? "var(--ink)" : "var(--grid)"} />
          <text x={LEFT - 6} y={y(t)} dy="0.35em" textAnchor="end" className="axislabel">
            {tickText(t)}
          </text>
        </g>
      ))}
      {years.map((row, i) => {
        const x = LEFT + i * slot + (slot - barW) / 2;
        const top = Math.min(y(row.value), y(0));
        const height = Math.abs(y(row.value) - y(0));
        return (
          <rect
            key={row.year}
            x={x}
            y={top}
            width={barW}
            height={Math.max(height, 0.5)}
            fill={row.value > 0 ? "var(--adds)" : "var(--reduces)"}
          >
            <title>{`FY${row.year}: ${money(row.value)}`}</title>
          </rect>
        );
      })}
      {first !== undefined ? (
        <text x={LEFT} y={H - 6} className="axislabel">
          FY{first}
        </text>
      ) : null}
      {last !== undefined && last !== first ? (
        <text x={W - RIGHT} y={H - 6} textAnchor="end" className="axislabel">
          FY{last}
        </text>
      ) : null}
    </svg>
  );
}
