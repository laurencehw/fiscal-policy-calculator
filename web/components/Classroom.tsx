"use client";
// One Classroom assignment: exercises at the chosen level, hints, answer checks on
// the engine, progress saved in this browser, and a printable submission.
import { useEffect, useRef, useState } from "react";
import {
  EMPTY_PROGRESS,
  LEVEL_LABELS,
  TYPE_LABELS,
  answerLabel,
  completed,
  defaultParams,
  formatAnswer,
  levelFrom,
  parseProgress,
  progressKey,
  stepDigits,
  type CheckResult,
  type ClassroomAssignment,
  type ClassroomExercise,
  type ExerciseProgress,
  type Level,
  type Progress,
} from "@/lib/classroom";

function load(key: string): Progress {
  try {
    return parseProgress(window.localStorage.getItem(key));
  } catch {
    return { ...EMPTY_PROGRESS, exercises: {} };
  }
}

function save(key: string, progress: Progress) {
  try {
    window.localStorage.setItem(key, JSON.stringify(progress));
  } catch {
    // Private windows and full storage: the page still works, it just forgets.
  }
}

export function Classroom({ assignment }: { assignment: ClassroomAssignment }) {
  const [level, setLevel] = useState<Level>(assignment.levels[0]);
  const [progress, setProgress] = useState<Progress>({ ...EMPTY_PROGRESS, exercises: {} });
  const [ready, setReady] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const first = levelFrom(new URLSearchParams(window.location.search).get("level"), assignment.levels);
    setLevel(first);
    setProgress(load(progressKey(assignment.id, first)));
    setReady(true);
  }, [assignment]);

  useEffect(() => {
    if (ready) save(progressKey(assignment.id, level), progress);
  }, [ready, assignment.id, level, progress]);

  function chooseLevel(next: Level) {
    setLevel(next);
    setProgress(load(progressKey(assignment.id, next)));
    setConfirmReset(false);
    const params = new URLSearchParams(window.location.search);
    params.set("level", next);
    window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
  }

  const update = (id: string, patch: Partial<ExerciseProgress>) =>
    setProgress((cur) => ({
      ...cur,
      exercises: { ...cur.exercises, [id]: { ...(cur.exercises[id] ?? { hints: 0, done: false }), ...patch } },
    }));

  const exercises = assignment.exercises.filter((e) => e.level === level);
  const done = completed(progress, exercises);

  return (
    <>
      <section className="classbar noprint">
        {assignment.levels.length > 1 ? (
          <div className="seg" role="group" aria-label="Level">
            {assignment.levels.map((l) => (
              <button key={l} type="button" aria-pressed={l === level} onClick={() => chooseLevel(l)}>
                {LEVEL_LABELS[l]}
              </button>
            ))}
          </div>
        ) : null}
        <div className="tailorform classnames">
          <label className="field">
            <span>Your name</span>
            <input type="text" value={progress.name} maxLength={200} onChange={(e) => setProgress((p) => ({ ...p, name: e.target.value }))} />
          </label>
          <label className="field">
            <span>Course</span>
            <input type="text" value={progress.course} maxLength={200} onChange={(e) => setProgress((p) => ({ ...p, course: e.target.value }))} />
          </label>
        </div>
        <p className="note">
          {done} of {exercises.length} exercises complete at the {LEVEL_LABELS[level].toLowerCase()} level. Saved in this browser.
        </p>
      </section>

      <div className="exercises noprint">
        {exercises.map((exercise, i) => (
          <Exercise
            key={`${level}-${exercise.id}`}
            n={i + 1}
            assignmentId={assignment.id}
            exercise={exercise}
            saved={progress.exercises[exercise.id]}
            update={(patch) => update(exercise.id, patch)}
          />
        ))}
      </div>

      <Submission assignment={assignment} level={level} exercises={exercises} progress={progress} />

      <div className="buttons tailorform noprint">
        <button type="button" onClick={() => window.print()}>
          Print or save as PDF
        </button>
        <button
          type="button"
          className="quiet"
          onClick={() => {
            if (!confirmReset) {
              setConfirmReset(true);
              return;
            }
            setProgress((p) => ({ ...p, exercises: {} }));
            setConfirmReset(false);
          }}
        >
          {confirmReset ? "Click again to clear every answer at this level" : "Start this level over"}
        </button>
      </div>
    </>
  );
}

type CheckState = { status: "idle" | "checking" } | { status: "error"; message: string };

function Exercise({
  n,
  assignmentId,
  exercise,
  saved,
  update,
}: {
  n: number;
  assignmentId: string;
  exercise: ClassroomExercise;
  saved: ExerciseProgress | undefined;
  update: (patch: Partial<ExerciseProgress>) => void;
}) {
  const [params, setParams] = useState<Record<string, number>>({ ...defaultParams(exercise), ...saved?.params });
  const [answer, setAnswer] = useState(saved?.answer === undefined ? "" : String(saved.answer));
  const [note, setNote] = useState(saved?.note ?? "");
  const [check, setCheck] = useState<CheckState>({ status: "idle" });
  const hints = saved?.hints ?? 0;
  const shown = exercise.hints.slice(0, hints);
  const unit = exercise.answer_unit || "$B";

  async function submit() {
    const value = Number(answer);
    if (answer.trim() === "" || !Number.isFinite(value)) {
      setCheck({ status: "error", message: "Enter a number as your answer." });
      return;
    }
    setCheck({ status: "checking" });
    try {
      const response = await fetch("/api/classroom/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assignment_id: assignmentId, exercise_id: exercise.id, params, answer: value, hints_used: hints }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        setCheck({ status: "error", message: data?.error ?? "The answer could not be checked. Try again in a moment." });
        return;
      }
      const r = data as CheckResult;
      setCheck({ status: "idle" });
      update({
        params: r.params,
        answer: value,
        correct: r.correct,
        done: r.correct || Boolean(saved?.done),
        model_answer: r.model_answer,
        unit: r.unit,
        feedback: r.feedback,
      });
    } catch {
      setCheck({ status: "error", message: "Could not reach the site. Check your connection and try again." });
    }
  }

  return (
    <section className="chart exercise">
      <div className="head">
        <h2>
          {n}. {exercise.title}
        </h2>
        <span className="tag">
          {TYPE_LABELS[exercise.type]}
          {saved?.done ? " · complete" : ""}
        </span>
      </div>
      <p className="prompt">{exercise.prompt}</p>

      <form
        className="tailorform"
        onSubmit={(e) => {
          e.preventDefault();
          if (exercise.checked) void submit();
          else update({ done: true, note });
        }}
      >
        {exercise.parameters.map((p) => {
          const digits = stepDigits(p.step);
          return (
            <label className="field" key={p.name}>
              <span>
                {p.label}: <b>{params[p.name].toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}</b>
              </span>
              <input
                type="range"
                min={p.min}
                max={p.max}
                step={p.step}
                value={params[p.name]}
                onChange={(e) => setParams((cur) => ({ ...cur, [p.name]: Number(e.target.value) }))}
              />
              {p.description ? <small className="q">{p.description}</small> : null}
            </label>
          );
        })}

        {exercise.hints.length ? (
          <div className="hints">
            {shown.map((h) => (
              <p key={h.level} className="hint">
                <b>Hint {h.level}.</b> {h.text}
              </p>
            ))}
            {hints < exercise.hints.length ? (
              <button type="button" className="quiet" onClick={() => update({ hints: hints + 1 })}>
                Show hint {hints + 1} of {exercise.hints.length}
              </button>
            ) : null}
          </div>
        ) : null}

        {exercise.checked ? (
          <>
            <label className="field">
              <span>{answerLabel(unit)}</span>
              <input type="number" step="any" inputMode="decimal" value={answer} onChange={(e) => setAnswer(e.target.value)} required />
            </label>
            <button type="submit" disabled={check.status === "checking"}>
              {check.status === "checking" ? "Checking…" : "Check my answer"}
            </button>
          </>
        ) : (
          <>
            <label className="field">
              <span>Your write-up</span>
              <textarea rows={8} value={note} maxLength={20000} onChange={(e) => setNote(e.target.value)} onBlur={() => update({ note })} />
            </label>
            <button type="submit">{saved?.done ? "Save" : "Mark complete"}</button>
          </>
        )}
      </form>

      <div aria-live="polite" className="feedback">
        {check.status === "checking" ? <p className="note">Checking on the engine. The first check after a quiet spell takes up to ten seconds.</p> : null}
        {check.status === "error" ? <p className="note warn">{check.message}</p> : null}
        {saved?.feedback && check.status === "idle" ? <p className={saved.correct ? "check" : "check no"}>{saved.feedback.replace(/\*\*/g, "")}</p> : null}
      </div>
      {saved?.done && exercise.insight ? (
        <div className="checked">
          <p>
            <b>Key insight.</b> {exercise.insight}
          </p>
        </div>
      ) : null}
    </section>
  );
}

function status(exercise: ClassroomExercise, saved: ExerciseProgress | undefined): string {
  if (!saved || (saved.answer === undefined && !saved.done)) return "Not attempted";
  if (!exercise.checked) return saved.done ? "Complete" : "Started";
  return saved.correct ? "Correct" : "Not yet correct";
}

function Submission({
  assignment,
  level,
  exercises,
  progress,
}: {
  assignment: ClassroomAssignment;
  level: Level;
  exercises: ClassroomExercise[];
  progress: Progress;
}) {
  const [today, setToday] = useState("");
  useEffect(() => setToday(new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })), []);
  return (
    <section className="chart submission">
      <div className="head">
        <h2>Submission</h2>
        <span className="tag">
          {LEVEL_LABELS[level]} · {completed(progress, exercises)} of {exercises.length} complete
        </span>
      </div>
      <p className="note">
        {progress.name || "Name not given"}
        {progress.course ? ` · ${progress.course}` : ""}
        {today ? ` · ${today}` : ""} · {assignment.title}
      </p>
      {exercises.map((exercise, i) => {
        const saved = progress.exercises[exercise.id];
        const unit = saved?.unit ?? exercise.answer_unit ?? "$B";
        return (
          <div className="subitem" key={exercise.id}>
            <h3>
              {i + 1}. {exercise.title} <small>{status(exercise, saved)}</small>
            </h3>
            {exercise.checked && saved?.answer !== undefined ? (
              <p>
                Answer {formatAnswer(saved.answer, unit)}
                {saved.model_answer !== null && saved.model_answer !== undefined ? ` · model ${formatAnswer(saved.model_answer, unit)}` : ""}
                {` · hints used ${saved.hints}`}
                {saved.params && exercise.parameters.length
                  ? ` · settings ${exercise.parameters
                      .map((p) => `${p.label.split(" (")[0]} ${(saved.params?.[p.name] ?? p.default).toLocaleString("en-US")}`)
                      .join(", ")}`
                  : ""}
              </p>
            ) : null}
            {!exercise.checked && saved?.note ? <p className="writeup">{saved.note}</p> : null}
          </div>
        );
      })}
      <p className="note">Answers are checked against the Fiscal Policy Calculator at the settings shown.</p>
    </section>
  );
}
