import assert from "node:assert/strict";
import { test } from "node:test";
import { answerLabel, completed, formatAnswer, levelFrom, parseProgress, progressKey, stepDigits, validateCheck, type ClassroomExercise } from "./classroom";

test("answers print in their own units, as the engine prints them", () => {
  assert.equal(formatAnswer(-265.7), "-$265.7B");
  assert.equal(formatAnswer(1353.9), "$1,353.9B");
  assert.equal(formatAnswer(15.77, "%"), "15.8%");
  assert.equal(formatAnswer(11, "policies"), "11 policies");
  assert.equal(formatAnswer(3.5, "pp"), "3.5 pp");
});

test("dollar answers carry the sign convention", () => {
  assert.match(answerLabel("$B"), /negative = revenue gain/);
  assert.doesNotMatch(answerLabel("%"), /revenue/);
});

test("a check request is held to ids, finite numbers and a few parameters", () => {
  const ok = validateCheck({ assignment_id: "laffer_curve", exercise_id: "laffer_ug_ex1", answer: -266, params: { rate_change: 0.02 }, hints_used: 2.7 });
  assert.deepEqual(ok, { assignment_id: "laffer_curve", exercise_id: "laffer_ug_ex1", params: { rate_change: 0.02 }, answer: -266, hints_used: 2 });
  assert.equal(typeof validateCheck({ assignment_id: "../x", exercise_id: "a", answer: 1 }), "string");
  assert.equal(typeof validateCheck({ assignment_id: "a", exercise_id: "b", answer: Number.NaN }), "string");
  assert.equal(typeof validateCheck({ assignment_id: "a", exercise_id: "b", answer: "1" }), "string");
  assert.equal(typeof validateCheck({ assignment_id: "a", exercise_id: "b", answer: 1, params: { "bad-name": 1 } }), "string");
  assert.equal(typeof validateCheck({ assignment_id: "a", exercise_id: "b", answer: 1, params: [1] }), "string");
});

test("saved progress keeps only well-formed fields", () => {
  assert.deepEqual(parseProgress(null), { name: "", course: "", exercises: {} });
  assert.deepEqual(parseProgress("not json"), { name: "", course: "", exercises: {} });
  const p = parseProgress(
    JSON.stringify({ name: "Ada", course: 7, exercises: { ex_1: { done: true, hints: 2, answer: 5, params: { a: 1, b: "x" } }, "bad id": { done: true } } }),
  );
  assert.equal(p.name, "Ada");
  assert.equal(p.course, "");
  assert.deepEqual(Object.keys(p.exercises), ["ex_1"]);
  assert.deepEqual(p.exercises.ex_1.params, { a: 1 });
  assert.equal(p.exercises.ex_1.done, true);
});

test("levels, keys, steps and counts", () => {
  assert.equal(levelFrom("graduate", ["undergraduate", "graduate"]), "graduate");
  assert.equal(levelFrom("advanced", ["undergraduate", "graduate"]), "undergraduate");
  assert.equal(progressKey("laffer_curve", "graduate"), "fpc-classroom:laffer_curve:graduate");
  assert.equal(stepDigits(0.01), 2);
  assert.equal(stepDigits(50000), 0);
  const ex = (id: string) => ({ id }) as ClassroomExercise;
  assert.equal(completed({ name: "", course: "", exercises: { a: { hints: 0, done: true }, b: { hints: 1, done: false } } }, [ex("a"), ex("b")]), 1);
});
