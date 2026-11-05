import { EstimateTag } from "@/components/EstimateTag";
import { money } from "@/lib/format";
import { estimateIdentity } from "@/lib/identity";
import { stripMarks, type HouseStripData } from "@/lib/houses";

function lead(subject: string, basis: string): string {
  const rest = basis ? basis.charAt(0).toUpperCase() + basis.slice(1) : "";
  if (subject && rest) return `${subject}. ${rest}.`;
  if (subject) return `${subject}.`;
  return rest ? `${rest}.` : "";
}

/** Where this score sits among the houses that published one. */
export function HouseStrip({ strip }: { strip: HouseStripData }) {
  const { marks, range } = stripMarks(strip);
  const houses = marks.filter((mark) => mark.kind === "house");
  const model = marks.find((mark) => mark.kind === "model");
  const sentence = lead(strip.subject, strip.basis);
  return (
    <section className="chart">
      <div className="head">
        <h2>Among other estimates</h2>
        {strip.window ? <span className="tag">{strip.window}</span> : null}
      </div>
      {sentence ? <p className="units">{sentence}</p> : null}
      <div
        className="track"
        role="img"
        aria-label={
          strip.range
            ? `${strip.range.label}. This calculator among the other published estimates`
            : "This calculator among the other published estimates"
        }
      >
        {range && strip.range ? <span className="rangelabel">{strip.range.label}</span> : null}
        {range ? <span className="span" style={{ left: `${range.left}%`, width: `${range.width}%` }} /> : null}
        {marks.map((mark) => (
          <span
            key={mark.key}
            className={mark.kind === "model" ? "model" : mark.fitted ? "dot fitted" : "dot"}
            style={{ left: `${mark.left}%` }}
            title={`${mark.label} ${money(mark.value)}`}
          />
        ))}
      </div>
      <ul className="houselist">
        {houses.map((mark) => (
          <li key={mark.key}>
            <span className={mark.fitted ? "swatch fitted" : "swatch"} />
            <EstimateTag
              short
              identity={estimateIdentity({ cbo_source: mark.label, budget_window: strip.window, credibility: null }, "published")}
            />
            {mark.fitted ? " (fitted target)" : ""}: {money(mark.value)}
          </li>
        ))}
        {model ? (
          <li>
            <span className="swatch model" />
            This calculator: {money(model.value)}
          </li>
        ) : null}
        {strip.range && houses.length === 0 ? (
          <li>
            {strip.range.label}: {money(strip.range.low_billions)} to {money(strip.range.high_billions)}
          </li>
        ) : null}
      </ul>
      {strip.caveat ? <p className="note">{strip.caveat}</p> : null}
    </section>
  );
}
