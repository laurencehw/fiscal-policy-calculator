"""Classroom Mode for the website: what a student may see, and answer checking.

The Streamlit app runs assignments in one process. The website splits them in
two. ``assignment_payload`` is the public half, written to the static export:
prompts, sliders, hints and the key insight, but never the instructor notes or
the numbers an answer is checked against (range bounds, model templates).
``check_exercise`` is the private half, served by the engine's
``POST /classroom/check``: it checks one answer and returns the same feedback
the Streamlit app shows.
"""

from __future__ import annotations

import math
from typing import Any

from .engine import (
    Assignment,
    AssignmentLoader,
    ComplexityLevel,
    Exercise,
    ExerciseRunner,
    ValidationMethod,
)
from .feedback import FeedbackEngine

LEVEL_LABELS = {
    ComplexityLevel.UNDERGRADUATE: "Undergraduate",
    ComplexityLevel.GRADUATE: "Graduate",
    ComplexityLevel.ADVANCED: "Advanced",
}


class UnknownExercise(LookupError):
    """The assignment or exercise id is not one the loader knows."""


def _exercise_payload(exercise: Exercise) -> dict[str, Any]:
    spec = exercise.validation
    method = spec.method if spec else ValidationMethod.NONE
    return {
        "id": exercise.id,
        "title": exercise.title,
        "type": exercise.type.value,
        "level": exercise.complexity.value,
        "prompt": exercise.prompt.strip(),
        "parameters": [
            {
                "name": p.name,
                "label": p.label,
                "min": p.min,
                "max": p.max,
                "step": p.step,
                "default": p.default,
                "unit": p.unit,
                "description": p.description,
            }
            for p in exercise.parameters
        ],
        "hints": [{"level": h.level, "text": h.text.strip()} for h in sorted(exercise.hints, key=lambda h: h.level)],
        # "none" exercises are written up and marked complete; the others are checked.
        "checked": method != ValidationMethod.NONE,
        "check": method.value,
        "answer_unit": spec.answer_unit if spec else "",
        "insight": exercise.expected_insight.strip(),
    }


def assignment_payload(assignment: Assignment) -> dict[str, Any]:
    """One assignment as the website shows it. Leaves out every answer."""
    return {
        "id": assignment.id,
        "title": assignment.title,
        "description": assignment.description.strip(),
        "levels": [level.value for level in assignment.complexity_levels],
        "objectives": list(assignment.learning_objectives),
        "minutes": assignment.estimated_minutes,
        "tags": list(assignment.tags),
        "exercises": [_exercise_payload(e) for e in assignment.exercises],
    }


def index_payload(loader: AssignmentLoader | None = None) -> list[dict[str, Any]]:
    """Every assignment, one line each, in the loader's order."""
    loader = loader or AssignmentLoader()
    rows = []
    for assignment_id in loader.list_assignments():
        a = loader.load(assignment_id)
        rows.append(
            {
                "id": a.id,
                "title": a.title,
                "description": a.description.strip(),
                "levels": [level.value for level in a.complexity_levels],
                "minutes": a.estimated_minutes,
                "exercises": {
                    level.value: len(a.exercises_for_level(level)) for level in a.complexity_levels
                },
            }
        )
    return rows


def _find(loader: AssignmentLoader, assignment_id: str, exercise_id: str) -> Exercise:
    if assignment_id not in loader.list_assignments():
        raise UnknownExercise(f"No assignment '{assignment_id}'")
    for exercise in loader.load(assignment_id).exercises:
        if exercise.id == exercise_id:
            return exercise
    raise UnknownExercise(f"No exercise '{exercise_id}' in '{assignment_id}'")


def _student_params(exercise: Exercise, sent: dict[str, float]) -> dict[str, float]:
    """The exercise's own parameters, defaulted and held to their slider range."""
    params = {}
    for p in exercise.parameters:
        value = sent.get(p.name, p.default)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            value = p.default
        params[p.name] = min(max(float(value), p.min), p.max)
    return params


def check_exercise(
    assignment_id: str,
    exercise_id: str,
    params: dict[str, float],
    answer: float,
    hints_used: int = 0,
    loader: AssignmentLoader | None = None,
) -> dict[str, Any]:
    """Check one answer. Raises ``UnknownExercise`` for an id the loader lacks."""
    loader = loader or AssignmentLoader()
    exercise = _find(loader, assignment_id, exercise_id)
    student_params = _student_params(exercise, params)
    result = ExerciseRunner().check_answer(exercise, student_params, answer)
    feedback = FeedbackEngine().generate(exercise, result, max(0, min(hints_used, 3)), exercise.complexity)
    # The site shows the key insight under the exercise itself once it is done.
    if exercise.expected_insight:
        feedback = feedback.replace(f"\n\n**Key insight:** {exercise.expected_insight}", "")
    return {
        "correct": result.correct,
        "answer": result.student_answer,
        "model_answer": result.model_answer,
        "pct_error": result.pct_error,
        "tolerance": result.tolerance,
        "unit": result.unit,
        "message": result.message,
        "feedback": feedback,
        "params": student_params,
    }
