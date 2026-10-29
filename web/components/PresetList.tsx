import Link from "next/link";
import { money, shortLabel } from "@/lib/format";
import { preset } from "@/lib/data";
import type { PresetInfo } from "@/lib/types";

/** One line per preset: the conventional score, and the published score when one exists. */
export function PresetList({ items }: { items: PresetInfo[] }) {
  return (
    <ul className="presetlist">
      {items.map((info) => {
        const figure = preset(info.id)?.conventional.ten_year_deficit_impact;
        return (
          <li key={info.id}>
            <Link href={`/explore/${info.id}`}>{shortLabel(info.name)}</Link>
            <span className="figs">
              {figure === undefined ? null : (
                <span className={`fig ${figure > 0 ? "adds" : "reduces"}`}>
                  {money(figure)}
                  <span className="figlabel">conventional</span>
                </span>
              )}
              {info.cbo_score === null || !info.cbo_published ? null : (
                <span className="fig published">
                  {money(info.cbo_score)}
                  <span className="figlabel">published</span>
                </span>
              )}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
