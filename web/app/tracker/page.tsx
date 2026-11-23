import type { Metadata } from "next";
import { trackerGroups, trackerIndex } from "@/lib/data";
import { TrackerLists } from "@/components/TrackerLists";
import type { TrackerRow } from "@/lib/types";
import { pageMeta } from "@/lib/meta";

export const metadata: Metadata = pageMeta({
  title: "Bill tracker",
  description: "Bills in Congress with a CBO ten-year cost estimate, plus the calculator's experimental readings of the rest.",
  path: "/tracker",
});

/** Only the fields the list shows, so the page does not ship every bill's sponsor and latest action. */
function slim(row: TrackerRow): TrackerRow {
  return {
    ...row,
    sponsor: "",
    latest_action: null,
    latest_action_date: null,
    introduced: null,
  };
}

function day(iso: string | null): string {
  return iso ? iso.slice(0, 10) : "";
}

export default function Tracker() {
  const index = trackerIndex();
  const { cbo, auto, autoLow } = trackerGroups(index);
  return (
    <>
      <header>
        <span className="eyebrow">Bill tracker</span>
        <h1>Bills with a budget estimate</h1>
        <p className="sentence">
          Of {index.bills.toLocaleString("en-US")} bills in the 119th Congress followed nightly,{" "}
          {cbo.length.toLocaleString("en-US")} have a CBO cost estimate. Another{" "}
          {(auto.length + autoLow.length).toLocaleString("en-US")} have an experimental reading by the calculator,
          hidden below by default. A positive figure adds to the deficit; a negative one reduces it. Updated{" "}
          {day(index.last_update)}.
        </p>
      </header>

      <TrackerLists cbo={cbo.map(slim)} auto={auto.map(slim)} autoLow={autoLow.map(slim)} />
    </>
  );
}
