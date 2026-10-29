import Link from "next/link";
import { money, shortLabel } from "@/lib/format";
import { preset } from "@/lib/data";
import type { PresetInfo } from "@/lib/types";

/** One line per preset: its name and its conventional ten-year figure. */
export function PresetList({ items }: { items: PresetInfo[] }) {
  return (
    <ul className="presetlist">
      {items.map((info) => {
        const figure = preset(info.id)?.conventional.ten_year_deficit_impact;
        return (
          <li key={info.id}>
            <Link href={`/explore/${info.id}`}>{shortLabel(info.name)}</Link>
            {figure === undefined ? null : (
              <span className={`fig ${figure > 0 ? "adds" : "reduces"}`}>{money(figure)}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
