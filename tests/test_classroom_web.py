"""Classroom Mode on the website: the public payload and ``POST /classroom/check``."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from classroom.engine import AssignmentLoader, RelativeValidator, ValidationMethod, format_answer
from classroom.web import UnknownExercise, assignment_payload, check_exercise, index_payload

LOADER = AssignmentLoader()
ALL = [(a, e) for a in LOADER.list_assignments() for e in LOADER.load(a).exercises]
MODEL_CHECKED = [(a, e) for a, e in ALL if e.validation and e.validation.method == ValidationMethod.RELATIVE_TO_MODEL]


@pytest.mark.parametrize(("assignment_id", "exercise"), MODEL_CHECKED, ids=[e.id for _, e in MODEL_CHECKED])
def test_every_model_checked_exercise_has_a_model_answer_at_its_defaults(assignment_id, exercise):
    # Two runners raised TypeError on every call, so those exercises failed
    # every student whatever they entered. A model answer must exist.
    defaults = {p.name: p.default for p in exercise.parameters}
    answer = RelativeValidator()._compute_model_answer(exercise.validation, defaults)
    assert answer is not None and answer == answer and answer != 0


def test_the_public_payload_carries_no_answers():
    text = json.dumps([assignment_payload(LOADER.load(a)) for a in LOADER.list_assignments()])
    for secret in ("min_acceptable", "max_acceptable", "policy_params", "target_field", "tolerance", "solution"):
        assert secret not in text
    for _, exercise in ALL:
        if exercise.solution_notes:
            assert exercise.solution_notes.strip()[:60] not in text


def test_the_index_lists_every_assignment_with_counts_by_level():
    rows = index_payload(LOADER)
    assert [r["id"] for r in rows] == LOADER.list_assignments()
    for row in rows:
        assert sum(row["exercises"].values()) == len(LOADER.load(row["id"]).exercises)


def test_a_model_answer_is_checked_at_the_students_own_settings():
    right = check_exercise("laffer_curve", "laffer_ug_ex1", {}, -266.0)
    assert right["correct"] and right["unit"] == "$B"
    assert "Key insight" not in right["feedback"]
    wrong = check_exercise("laffer_curve", "laffer_ug_ex1", {}, -100.0)
    assert not wrong["correct"]
    assert "-$265.7B" in wrong["feedback"]


def test_sliders_are_held_to_their_range_and_unknown_names_are_dropped():
    result = check_exercise("laffer_curve", "laffer_ug_ex1", {"rate_change": 9.0, "junk": 1.0}, -1.0)
    assert result["params"] == {"rate_change": 0.10, "affected_income_threshold": 400000.0}


def test_a_range_answer_reports_in_its_own_unit():
    result = check_exercise("progressive_vs_flat", "flat_ug_ex2", {}, 50.0)
    assert not result["correct"] and result["unit"] == "%"
    assert "$" not in result["message"]


def test_unknown_ids_are_refused():
    with pytest.raises(UnknownExercise):
        check_exercise("laffer_curve", "nope", {}, 1.0)
    with pytest.raises(UnknownExercise):
        check_exercise("../etc", "x", {}, 1.0)


def test_answers_print_in_their_units():
    assert format_answer(-265.7) == "-$265.7B"
    assert format_answer(1353.9) == "$1,353.9B"
    assert format_answer(15.77, "%") == "15.8%"
    assert format_answer(11, "policies") == "11 policies"
    assert format_answer(3.5, "pp") == "3.5 pp"


def test_the_endpoint(monkeypatch):
    monkeypatch.delenv("FISCAL_API_KEYS", raising=False)
    import api

    client = TestClient(api.app)
    ok = client.post(
        "/classroom/check",
        json={"assignment_id": "olg_generational", "exercise_id": "olg_ug_ex1", "answer": 15.8},
    )
    assert ok.status_code == 200 and ok.json()["correct"]
    missing = client.post("/classroom/check", json={"assignment_id": "x", "exercise_id": "y", "answer": 1})
    assert missing.status_code == 404
    bad = client.post(
        "/classroom/check",
        json={"assignment_id": "laffer_curve", "exercise_id": "laffer_ug_ex1", "answer": "NaN"},
    )
    assert bad.status_code in (400, 422)
