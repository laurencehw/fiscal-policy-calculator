import type { Evidence } from "@/lib/types";
import { CLASS_STYLE, FRAME, bandPolygon, domain, points, scaler, ticks } from "@/lib/scatter";

const tickLabel = (v: number) => (v >= 1000 ? `$${v / 1000}T` : `$${v}B`);

/** Plan C3: each out-of-sample row, model against published, on log scales. Server-rendered SVG. */
export default function OutOfSampleScatter({ ev }: { ev: Evidence }) {
  const rows = ev.out_of_sample_rows;
  const dom = domain(rows);
  const s = scaler(dom);
  const pts = points(rows, dom);
  const [lo, hi] = dom;
  const bottom = FRAME.height - FRAME.bottom;
  const right = FRAME.width - FRAME.right;
  const label = (slug: string) => {
    const l = ev.out_of_sample_classes[slug]?.label ?? slug;
    return l[0].toUpperCase() + l.slice(1);
  };
  return (
    <figure className="oosscatter">
      <svg
        viewBox={`0 0 ${FRAME.width} ${FRAME.height}`}
        role="img"
        aria-labelledby="oos-scatter-title oos-scatter-desc"
        style={{ width: "100%", height: "auto", maxWidth: FRAME.width }}
      >
        <title id="oos-scatter-title">{`Model against published score for ${rows.length} out-of-sample predictions`}</title>
        <desc id="oos-scatter-desc">
          {`Both axes are ten-year magnitudes on log scales. Points on the diagonal match the published score exactly. ${ev.out_of_sample.within_15pct} of ${rows.length} sit inside the inner band (within 15%) and ${ev.out_of_sample.within_25pct} inside the outer band (within 25%).`}
        </desc>
        <polygon points={bandPolygon(dom, 0.25)} fill="var(--grid)" opacity={0.6} />
        <polygon points={bandPolygon(dom, 0.15)} fill="var(--grid)" />
        {ticks(dom).map((t) => (
          <g key={t} fontSize={11} fill="var(--muted)" fontFamily="var(--label)">
            <line x1={s.x(t)} x2={s.x(t)} y1={FRAME.top} y2={bottom} stroke="var(--rule)" strokeWidth={0.5} />
            <line x1={FRAME.left} x2={right} y1={s.y(t)} y2={s.y(t)} stroke="var(--rule)" strokeWidth={0.5} />
            <text x={s.x(t)} y={bottom + 16} textAnchor="middle">
              {tickLabel(t)}
            </text>
            <text x={FRAME.left - 6} y={s.y(t) + 4} textAnchor="end">
              {tickLabel(t)}
            </text>
          </g>
        ))}
        <line x1={s.x(lo)} y1={s.y(lo)} x2={s.x(hi)} y2={s.y(hi)} stroke="var(--muted)" strokeDasharray="4 3" />
        <text
          x={(FRAME.left + right) / 2}
          y={FRAME.height - 6}
          textAnchor="middle"
          fontSize={12}
          fill="var(--muted)"
          fontFamily="var(--label)"
        >
          Published score (ten-year, absolute)
        </text>
        <text
          transform={`translate(14 ${(FRAME.top + bottom) / 2}) rotate(-90)`}
          textAnchor="middle"
          fontSize={12}
          fill="var(--muted)"
          fontFamily="var(--label)"
        >
          Model score
        </text>
        {pts.map((p) => {
          const st = CLASS_STYLE[p.class] ?? { color: "var(--muted)", shape: "circle" as const };
          const tip = `${p.policy_id}: model ${p.model.toFixed(1)}, published ${p.published.toFixed(1)} ($B), ${p.error}% apart`;
          return st.shape === "square" ? (
            <rect
              key={p.policy_id}
              x={p.cx - 4}
              y={p.cy - 4}
              width={8}
              height={8}
              fill={st.hollow ? "var(--paper)" : st.color}
              stroke={st.color}
              strokeWidth={1.5}
            >
              <title>{tip}</title>
            </rect>
          ) : (
            <circle
              key={p.policy_id}
              cx={p.cx}
              cy={p.cy}
              r={4.5}
              fill={st.color}
              fillOpacity={0.85}
              stroke="var(--paper)"
              strokeWidth={0.75}
            >
              <title>{tip}</title>
            </circle>
          );
        })}
      </svg>
      <figcaption>
        <ul className="oosscatter-key">
          {Object.entries(CLASS_STYLE)
            .filter(([slug]) => ev.out_of_sample_classes[slug])
            .map(([slug, st]) => (
              <li key={slug}>
                <svg width={12} height={12} aria-hidden="true">
                  {st.shape === "square" ? (
                    <rect x={2} y={2} width={8} height={8} fill={st.hollow ? "none" : st.color} stroke={st.color} strokeWidth={1.5} />
                  ) : (
                    <circle cx={6} cy={6} r={4.5} fill={st.color} />
                  )}
                </svg>
                {label(slug)} ({ev.out_of_sample_classes[slug].n})
              </li>
            ))}
        </ul>
        <p className="source">
          Dashed line: model equals published. Shaded bands: within 15% (darker) and within 25%. Every point is a
          prediction registered before its published score was compared. Source: the calculator&apos;s validation
          report.
        </p>
      </figcaption>
    </figure>
  );
}
