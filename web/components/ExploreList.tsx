"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { arrange, filterRows, scaleOf, type ExploreRow, type ExploreSort } from "@/lib/explore";
import { money } from "@/lib/format";

function Bar({ value, scale, published }: { value: number; scale: number; published?: boolean }) {
  const width = `${Math.max(1, (Math.abs(value) / scale) * 100)}%`;
  const tone = published ? "published" : value > 0 ? "adds" : "reduces";
  return (
    <span className="bartrack" aria-hidden="true">
      <span className={`bar ${tone}`} style={{ width }} />
    </span>
  );
}

/** Explore's list: a filter box, a sort toggle, and one bar per figure on a shared scale. */
export function ExploreList({ rows }: { rows: ExploreRow[] }) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<ExploreSort>("topic");
  const scale = useMemo(() => scaleOf(rows), [rows]);
  const shown = filterRows(rows, query);
  const groups = arrange(shown, sort);
  return (
    <div className="explore">
      <div className="exploretools">
        <label className="search">
          <span className="sr-only">Filter proposals</span>
          <input
            type="search"
            placeholder="Filter, e.g. corporate, tariff, SALT"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <div className="seg" role="group" aria-label="Order">
          <button type="button" aria-pressed={sort === "topic"} onClick={() => setSort("topic")}>
            By topic
          </button>
          <button type="button" aria-pressed={sort === "size"} onClick={() => setSort("size")}>
            Largest first
          </button>
        </div>
      </div>
      <p className="note" aria-live="polite">
        {shown.length === rows.length ? `${rows.length} proposals.` : `${shown.length} of ${rows.length} proposals.`}
        {shown.length === 0 ? " Nothing matches; try a shorter word." : null}
      </p>
      <div className="presetgroups">
        {groups.map((group) => (
          <section key={group.area ?? "all"} className="presetgroup">
            {group.area ? <h2>{group.area}</h2> : null}
            <ul className="presetlist explorelist">
              <li className="explorehead" aria-hidden="true">
                <span />
                <span className="figlabel">Calculator</span>
                <span className="figlabel">Published</span>
              </li>
              {group.rows.map((row) => (
                <li key={row.id}>
                  <Link href={`/explore/${row.id}`}>{row.name}</Link>
                  <span className="figcell">
                    {row.conventional === null ? null : (
                      <>
                        <span className={`fig ${row.conventional > 0 ? "adds" : "reduces"}`}>
                          <span className="sr-only">Calculator: </span>
                          {money(row.conventional)}
                        </span>
                        <Bar value={row.conventional} scale={scale} />
                      </>
                    )}
                  </span>
                  <span className="figcell">
                    {row.published === null ? (
                      <span className="fig published none">none</span>
                    ) : (
                      <>
                        <span className="fig published">
                          <span className="sr-only">Published: </span>
                          {money(row.published)}
                        </span>
                        <Bar value={row.published} scale={scale} published />
                      </>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
