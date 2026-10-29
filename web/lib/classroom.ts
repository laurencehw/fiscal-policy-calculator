// Classroom Mode: assignment types, answer formatting, request checks and the
// student's saved progress. Pure functions, so the tests run without a browser.

export const LEVELS = ["undergraduate", "graduate", "advanced"] as const;
export type Level = (typeof LEVELS)[number];
export const LEVEL_LABELS: Record<Level, string> = {
  undergraduate: "Undergraduate",
  graduate: "Graduate",
  advanced: "Advanced",
};

export type ClassroomParam = {
  name: string;
  label: string;
  min: number;
  max: number;
  step: number;
  default: number;
  unit: string;
  description: string;
};

export type ClassroomExercise = {
  id: string;
  title: string;
  type: "parameter_exploration" | "target_finding" | "comparison" | "open_analysis";
  level: Level;
  prompt: string;
  parameters: ClassroomParam[];
  hints: { level: number; text: string }[];
  checked: boolean;
  check: "relative_to_model" | "range_check" | "qualitative" | "none";
  answer_unit: string;
  insight: string;
};

export type ClassroomAssignment = {
  id: string;
  title: string;
  description: string;
  levels: Level[];
  objectives: string[];
  minutes: number;
  tags: string[];
  exercises: ClassroomExercise[];
};

export type ClassroomIndexRow = {
  id: string;
  title: string;
  description: string;
  levels: Level[];
  minutes: number;
  exercises: Partial<Record<Level, number>>;
};

export type CheckResult = {
  correct: boolean;
  answer: number;
  model_answer: number | null;
  pct_error: number | null;
  tolerance: number;
  unit: string;
  message: string;
  feedback: string;
  params: Record<string, number>;
};

export const TYPE_LABELS: Record<ClassroomExercise["type"], string> = {
  parameter_exploration: "Explore",
  target_finding: "Find the target",
  comparison: "Compare",
  open_analysis: "Write-up",
};

/** One answer in its own unit, as the engine prints it: -$265.7B, 15.8%, 3.5 pp. */
export function formatAnswer(value: number, unit = "$B"): string {
  if (unit === "$B") {
    const body = Math.abs(value).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    return `${value < 0 ? "-" : ""}$${body}B`;
  }
  if (unit === "%") return `${value.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
  const digits = Number.isInteger(value) ? 0 : 1;
  return `${value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })} ${unit}`;
}

/** What the answer box asks for. Dollar answers carry the sign convention. */
export function answerLabel(unit: string): string {
  if (unit === "$B") return "Your answer, billions of dollars (negative = revenue gain, deficit falls)";
  if (unit === "%") return "Your answer, percent";
  if (unit === "pp") return "Your answer, percentage points";
  return `Your answer, ${unit}`;
}

export function defaultParams(exercise: ClassroomExercise): Record<string, number> {
  return Object.fromEntries(exercise.parameters.map((p) => [p.name, p.default]));
}

/** Decimal places a slider's step needs. */
export function stepDigits(step: number): number {
  const text = String(step);
  return text.includes(".") ? text.split(".")[1].length : 0;
}

export function levelFrom(value: string | null, levels: Level[]): Level {
  return levels.find((l) => l === value) ?? levels[0] ?? "undergraduate";
}

const ID = /^[a-z0-9_]{1,64}$/;

export type CheckRequest = {
  assignment_id: string;
  exercise_id: string;
  params: Record<string, number>;
  answer: number;
  hints_used: number;
};

/** The body the site forwards to the engine's /classroom/check, or why it was refused. */
export function validateCheck(body: unknown): CheckRequest | string {
  if (!body || typeof body !== "object") return "Expected an object.";
  const b = body as Record<string, unknown>;
  if (typeof b.assignment_id !== "string" || !ID.test(b.assignment_id)) return "Unknown assignment.";
  if (typeof b.exercise_id !== "string" || !ID.test(b.exercise_id)) return "Unknown exercise.";
  if (typeof b.answer !== "number" || !Number.isFinite(b.answer)) return "Enter a number as your answer.";
  if (Math.abs(b.answer) > 1e9) return "That answer is out of range.";
  const params: Record<string, number> = {};
  if (b.params !== undefined) {
    if (!b.params || typeof b.params !== "object" || Array.isArray(b.params)) return "Parameters must be an object.";
    const entries = Object.entries(b.params as Record<string, unknown>);
    if (entries.length > 20) return "Too many parameters.";
    for (const [name, value] of entries) {
      if (!ID.test(name) || typeof value !== "number" || !Number.isFinite(value)) return `Bad parameter ${name.slice(0, 40)}.`;
      params[name] = value;
    }
  }
  const hints = typeof b.hints_used === "number" && Number.isFinite(b.hints_used) ? Math.max(0, Math.min(10, Math.trunc(b.hints_used))) : 0;
  return { assignment_id: b.assignment_id, exercise_id: b.exercise_id, params, answer: b.answer, hints_used: hints };
}

// ---- Saved progress (one record per assignment and level, in the browser) ----

export type ExerciseProgress = {
  params?: Record<string, number>;
  answer?: number;
  hints: number;
  done: boolean;
  correct?: boolean;
  model_answer?: number | null;
  unit?: string;
  feedback?: string;
  note?: string;
};

export type Progress = {
  name: string;
  course: string;
  exercises: Record<string, ExerciseProgress>;
};

export const EMPTY_PROGRESS: Progress = { name: "", course: "", exercises: {} };

export function progressKey(assignmentId: string, level: Level): string {
  return `fpc-classroom:${assignmentId}:${level}`;
}

const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const text = (v: unknown, max: number) => (typeof v === "string" ? v.slice(0, max) : undefined);

/** Read saved progress, keeping only well-formed fields. Anything else starts fresh. */
export function parseProgress(raw: string | null): Progress {
  if (!raw) return { ...EMPTY_PROGRESS, exercises: {} };
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return { ...EMPTY_PROGRESS, exercises: {} };
  }
  if (!data || typeof data !== "object") return { ...EMPTY_PROGRESS, exercises: {} };
  const d = data as Record<string, unknown>;
  const exercises: Record<string, ExerciseProgress> = {};
  if (d.exercises && typeof d.exercises === "object") {
    for (const [id, value] of Object.entries(d.exercises as Record<string, unknown>)) {
      if (!ID.test(id) || !value || typeof value !== "object") continue;
      const v = value as Record<string, unknown>;
      const params =
        v.params && typeof v.params === "object"
          ? Object.fromEntries(Object.entries(v.params as Record<string, unknown>).filter((e): e is [string, number] => finite(e[1])))
          : undefined;
      exercises[id] = {
        params,
        answer: finite(v.answer) ? v.answer : undefined,
        hints: finite(v.hints) ? Math.max(0, Math.trunc(v.hints)) : 0,
        done: v.done === true,
        correct: typeof v.correct === "boolean" ? v.correct : undefined,
        model_answer: finite(v.model_answer) ? v.model_answer : null,
        unit: text(v.unit, 20),
        feedback: text(v.feedback, 2000),
        note: text(v.note, 20000),
      };
    }
  }
  return { name: text(d.name, 200) ?? "", course: text(d.course, 200) ?? "", exercises };
}

export function completed(progress: Progress, exercises: ClassroomExercise[]): number {
  return exercises.filter((e) => progress.exercises[e.id]?.done).length;
}
