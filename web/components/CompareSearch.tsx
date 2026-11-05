"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

/** Adds or removes a proposal by rewriting ?ids=, so the server render stays the page. */
export function CompareSearch({
  catalog,
  selected,
}: {
  catalog: { id: string; name: string }[];
  selected: string[];
}) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const names = new Map(catalog.map((row) => [row.id, row.name]));
  const matches = catalog
    .filter((row) => !selected.includes(row.id) && row.name.toLowerCase().includes(query.trim().toLowerCase()))
    .slice(0, 8);

  function go(ids: string[]) {
    router.push(ids.length ? `/compare?ids=${ids.join(",")}` : "/compare");
    setQuery("");
  }

  return (
    <form
      className="exploretools"
      onSubmit={(event) => {
        event.preventDefault();
        if (matches[0] && selected.length < 3) go([...selected, matches[0].id]);
      }}
    >
      <label className="search">
        <span className="sr-only">Add a proposal</span>
        <input
          type="search"
          placeholder={selected.length >= 3 ? "Three is the most this page holds" : "Add a proposal"}
          value={query}
          disabled={selected.length >= 3}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      {query && matches.length ? (
        <ul className="compmatches">
          {matches.map((row) => (
            <li key={row.id}>
              <button type="button" onClick={() => go([...selected, row.id])}>
                {row.name}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {selected.length ? (
        <ul className="compmatches">
          {selected.map((id) => (
            <li key={id}>
              <button type="button" onClick={() => go(selected.filter((other) => other !== id))}>
                Remove {names.get(id) ?? id}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </form>
  );
}
