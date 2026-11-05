import type { Metadata } from "next";
import Link from "next/link";
import { CATEGORY_LABEL, CHANGES_DAYS, byDate, changeSentence, recentChanges } from "@/lib/changes";
import { changes, manifest } from "@/lib/data";
import { shortLabel } from "@/lib/format";
import { longDate } from "@/lib/share";

export const metadata: Metadata = {
  title: "What changed",
  description: "Scores that moved and new CBO estimates, from the last thirty days of nightly exports.",
  alternates: { canonical: "/changes" },
};

// Re-read hourly so "the last 30 days" is counted from today, not from the build.
export const revalidate = 3600;

export default function ChangesPage() {
  const file = changes();
  const today = new Date().toISOString().slice(0, 10);
  const groups = byDate(recentChanges(file.items, today));
  const scoresDate = manifest().scores_date;
  const threshold = `${(file.threshold * 100).toFixed(1)}%`;
  return (
    <div className="work">
      <header>
        <span className="eyebrow">What changed</span>
        <h1>What changed</h1>
        <p className="sentence">
          Each night I re-run every preset and pull new bills. This page lists what moved in the last {CHANGES_DAYS}{" "}
          days, newest first: a preset whose score moved by more than {threshold}, a new CBO estimate in the tracker, or
          a new baseline.
        </p>
        <p className="note">
          A score change means the calculator&apos;s own figure moved. A data refresh means something it reads moved,
          such as a CBO estimate or the baseline.
          {scoresDate ? ` The scores were last recomputed on ${longDate(scoresDate)}.` : ""}
        </p>
      </header>

      {groups.length ? (
        groups.map((group) => (
          <section className="changes" key={group.date} aria-labelledby={`day-${group.date}`}>
            <h2 id={`day-${group.date}`}>{longDate(group.date)}</h2>
            <ul className="marked changelist">
              {group.items.map((item) => (
                <li key={`${item.kind}-${item.id}`} className={`change ${item.category}`}>
                  <span className="tag">{CATEGORY_LABEL[item.category]}</span>{" "}
                  {item.href.startsWith("/") ? (
                    <Link href={item.href}>{item.kind === "preset" ? shortLabel(item.title) : item.title}</Link>
                  ) : (
                    <a href={item.href}>{item.title}</a>
                  )}
                  . {changeSentence(item)}
                </li>
              ))}
            </ul>
          </section>
        ))
      ) : (
        <p className="note">
          Nothing has moved in the last {CHANGES_DAYS} days. A night with no change writes nothing here.
        </p>
      )}
    </div>
  );
}
