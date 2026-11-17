import { money } from "@/lib/format";
import type { LawStatus } from "@/lib/types";

/**
 * For a pre-2025-law preset: what it scores on the site's own current-law baseline,
 * shown above the stored pre-2025 figure so a reader sees the number for today first.
 */
export function CurrentLawAnswer({
  status,
  figure,
  vintage,
  sameAsName,
}: {
  status: LawStatus;
  figure: number | null;
  vintage: string;
  sameAsName: string | null;
}) {
  const answer = status.current_law;
  if (!status.pre_2025_law || !answer) return null;
  const value =
    answer.kind === "already_law" ? "$0" : figure === null ? "Not scored" : money(figure);
  const tone = figure === null || figure === 0 ? "" : figure > 0 ? "adds" : "reduces";
  return (
    <section className="currentlawanswer" aria-label="On current law">
      <div className="stage">
        <span className="q">Against current law (CBO {vintage} baseline, which includes P.L. 119-21)</span>
        <span className={`v ${tone}`}>{value}</span>
        <span className="q">
          {answer.kind === "already_law"
            ? "Already law, so nothing to add"
            : answer.kind === "same_as"
              ? `The same question as ${sameAsName ?? "another proposal"}`
              : "Part of this is already law; the rest is not scored"}
        </span>
      </div>
      <p className="sentence">
        {answer.reason}{" "}
        {answer.kind === "same_as" ? (
          <a href={answer.url}>See {sameAsName ?? "that proposal"}.</a>
        ) : (
          <>
            Source: <a href={answer.url}>{answer.source}</a>.
          </>
        )}
      </p>
      <p className="note">The figures below are the pre-2025-law score this proposal was built to answer.</p>
    </section>
  );
}
