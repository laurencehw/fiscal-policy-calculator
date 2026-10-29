import type { Metadata } from "next";
import Link from "next/link";
import { LEVEL_LABELS } from "@/lib/classroom";
import { classroomIndex } from "@/lib/data";

export const metadata: Metadata = {
  title: "Classroom",
  description: "Problem sets in public finance that check each answer against the model, with hints, saved progress and a printable submission.",
  alternates: { canonical: "/classroom" },
};

export default function ClassroomPage() {
  const rows = classroomIndex();
  return (
    <>
      <header>
        <span className="eyebrow">Classroom</span>
        <h1>Problem sets that check against the model</h1>
        <p className="sentence">
          Each assignment asks you to estimate something by hand, then checks your answer. Where an answer depends on the model, it is
          checked against a fresh run at your own settings, so the problem sets stay right when the baseline is updated.
        </p>
        <p className="note">
          Progress is saved in this browser only. When you finish, print the submission page or save it as a PDF to hand in.
        </p>
      </header>
      <ul className="presetlist">
        {rows.map((row) => (
          <li key={row.id}>
            <span>
              <Link href={`/classroom/${row.id}`}>{row.title}</Link>
              <small className="classmeta">
                {row.levels.map((l) => `${LEVEL_LABELS[l]} (${row.exercises[l] ?? 0})`).join(" · ")}
              </small>
            </span>
            <span className="fig">{row.minutes} min</span>
          </li>
        ))}
      </ul>
      <p className="note">
        Instructors: the link to an assignment opens at the level in its address, for example <code>?level=graduate</code>. Tailor can
        also make a frozen link that pins a policy and the baseline for a whole class; open Tailor with <code>?classroom=1</code>.
      </p>
    </>
  );
}
