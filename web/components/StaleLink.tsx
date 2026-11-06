"use client";
// The notice an old share link gets: the figures behind it have been
// recomputed since it was made. Read on the client so static pages stay static.
import { useEffect, useState } from "react";
import { linkVersion, staleNotice } from "@/lib/share";

export function StaleLink({ scoresDate }: { scoresDate: string }) {
  const [text, setText] = useState<string | null>(null);
  useEffect(() => {
    const v = linkVersion(new URLSearchParams(window.location.search).get("v"));
    setText(staleNotice(v, scoresDate));
  }, [scoresDate]);
  if (!text) return null;
  return (
    <p className="note stalelink" role="status">
      {text} <a href="/changes">See what changed</a>.
    </p>
  );
}
