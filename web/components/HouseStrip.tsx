import { stripMarks, type HouseStripData } from "@/lib/houses";
import { money } from "@/lib/format";

/** Where this score sits among the houses that published one. */
export function HouseStrip({ strip }: { strip: HouseStripData }) {
  const { marks, range } = stripMarks(strip);
  const houses = marks.filter((mark) => mark.kind === "house");
  const model = marks.find((mark) => mark.kind === "model");
  return (
    <section className="chart">
      <div className="head">
        <h2>Among other estimates</h2>
        {strip.window ? <span className="tag">{strip.window}</span> : null}
      </div>
      {strip.subject ? <p className="units">{strip.subject}. {strip.basis}.</p> : null}
      <div className="track" role="img" aria-label="This calculator among the other published estimates">
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
            {mark.label}
            {mark.fitted ? " (fitted target)" : ""}: {money(mark.value)}
          </li>
        ))}
        {model ? (
          <li>
            <span className="swatch model" />
            This calculator: {money(model.value)}
          </li>
        ) : null}
        {strip.range ? (
          <li>
            Published range, {strip.range.source_name}: {money(strip.range.low_billions)} to {money(strip.range.high_billions)}
          </li>
        ) : null}
      </ul>
      {strip.caveat ? <p className="note">{strip.caveat}</p> : null}
    </section>
  );
}
