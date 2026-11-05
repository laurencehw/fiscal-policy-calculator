"use client";

import Link from "next/link";
import { useState } from "react";
import { MAX_COMPARE, compareHref, toggleId } from "@/lib/compare";

export type CompareOption = { id: string; name: string; area: string };

/** The picker: type part of a name, follow a link to add it. Each link is the new URL. */
export function CompareSearch({ options, ids }: { options: CompareOption[]; ids: string[] }) {
  const [query, setQuery] = useState("");
  const full = ids.length >= MAX_COMPARE;
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  const matches = words.length
    ? options
        .filter((option) => !ids.includes(option.id))
        .filter((option) => words.every((word) => `${option.name} ${option.area}`.toLowerCase().includes(word)))
        .slice(0, 8)
    : [];
  return (
    <div className="comparesearch exploretools">
      <label className="search">
        <span className="sr-only">Find a proposal to compare</span>
        <input
          type="search"
          placeholder={full ? "Remove one to add another" : "Add a proposal, e.g. tariff, estate, SALT"}
          value={query}
          disabled={full}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      <p className="note" aria-live="polite">
        {full
          ? `Comparing ${MAX_COMPARE}, the most this page shows.`
          : words.length && matches.length === 0
            ? "Nothing matches; try a shorter word."
            : `${ids.length} of ${MAX_COMPARE} chosen.`}
      </p>
      {matches.length ? (
        <ul className="matches">
          {matches.map((option) => (
            <li key={option.id}>
              <Link href={compareHref(toggleId(ids, option.id))} onClick={() => setQuery("")}>
                Add {option.name}
              </Link>
              <span className="tag">{option.area}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
