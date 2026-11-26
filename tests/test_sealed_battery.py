"""The sealed battery's rules (``fiscal_model/validation/sealed.py``)."""

from __future__ import annotations

from fiscal_model.validation.cbo_scores import KNOWN_SCORES, validation_shape
from fiscal_model.validation.sealed import LOCK_DATE, RETIRED, SEALED_CASES, sealed_cases


def test_no_sealed_row_is_in_the_scorecard():
    # Rule 2: never pooled. A sealed id in KNOWN_SCORES would put it in a tier.
    for case in SEALED_CASES:
        assert case.case_id not in KNOWN_SCORES
        assert case.score.policy_id == case.case_id


def test_ids_are_unique_and_entered_on_or_after_the_lock():
    ids = [c.case_id for c in SEALED_CASES]
    assert len(ids) == len(set(ids))
    for case in SEALED_CASES:
        assert case.entered_date >= LOCK_DATE


def test_the_battery_holds_tax_cuts_and_rises():
    # Rule 4: the sign the 44 rows cannot test.
    costs = [c.score.ten_year_cost for c in sealed_cases()]
    assert any(cost > 0 for cost in costs)
    assert any(cost < 0 for cost in costs)


def test_every_row_has_a_generic_shape_and_a_source_page():
    # Rule 5: expressible by the generic path with no new code.
    for case in SEALED_CASES:
        assert validation_shape(case.score) is not None
        assert case.read_from.startswith("https://")
        assert case.score.source_url == case.read_from


def test_no_tax_foundation_corporate_row():
    # Rule 5: Tax Foundation sets the corporate credit factor.
    for case in SEALED_CASES:
        if case.score.source.value == "Tax Foundation":
            assert case.score.policy_type != "corporate_tax"


def test_retired_rows_name_a_sealed_row_and_a_reason():
    ids = {c.case_id for c in SEALED_CASES}
    for case_id, reason in RETIRED.items():
        assert case_id in ids
        assert reason.strip()


def test_the_report_lists_unscored_rows_without_scoring_them():
    from scripts.sealed_battery import build_report

    report = build_report()
    assert report["summary"]["entered"] == len(sealed_cases())
    for row in report["rows"]:
        if not row["scoring_enabled"]:
            assert "model_10yr_billions" not in row
