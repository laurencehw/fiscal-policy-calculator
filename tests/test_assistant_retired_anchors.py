"""The Ask headline must never be anchored on a row whose target was retired.

Defect (2026-10 hunt): ``candidate_anchors`` took every ``KNOWN_SCORES``
record with a matching family and non-zero rate change, including the four
targets PR #162 retired for want of a document (and ``top_rate_45`` before
them). A request for a 3pp across-the-board rate *cut* was headlined at +$600B
by scaling the retired ``illustrative_500k_2pp`` (+$400B) while the engine said
$3,855B, and the capability gate told the model to "answer from the anchors".
"""

from __future__ import annotations

import pytest

from fiscal_model.assistant.benchmarks import (
    build_capability_gate,
    candidate_anchors,
    retired_policy_ids,
)
from fiscal_model.validation.cbo_scores import KNOWN_SCORES
from fiscal_model.validation.preregistered import live_cases, retired_cases

PR_162_RETIRED = {
    "illustrative_500k_2pp",
    "medicare_surcharge_2pp",
    "illustrative_top_rate_5pp",
    "warren_ultramillionaire_surtax_3pp",
}


def test_retired_set_is_derived_from_the_manifest() -> None:
    expected = {c.policy_id for c in retired_cases()} - set(live_cases())
    assert retired_policy_ids() == expected
    assert PR_162_RETIRED <= retired_policy_ids()


_GRID = [
    (pt, rate, thr)
    for pt in ("income_tax", "corporate_tax", "capital_gains_tax")
    for rate in (-0.10, -0.05, -0.03, -0.02, -0.01, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10)
    for thr in (0.0, 20_000.0, 100_000.0, 400_000.0, 500_000.0, 609_350.0, 1_000_000.0, 2_000_000.0)
]


def test_no_retired_id_is_ever_an_anchor() -> None:
    retired = retired_policy_ids()
    assert retired, "the manifest has retired rows; the set must not be empty"
    for pt, rate, thr in _GRID:
        for anchor in candidate_anchors(pt, rate, thr):
            assert anchor.policy_id not in retired, (pt, rate, thr, anchor.policy_id)


@pytest.mark.parametrize("retired_id", sorted(PR_162_RETIRED))
def test_retired_rows_are_still_in_known_scores(retired_id: str) -> None:
    """The fix is a filter at the anchor, not a deletion: the row keeps its
    scorecard entry (a retired target is withdrawn, never deleted)."""
    assert retired_id in KNOWN_SCORES


def test_the_three_point_cut_repro_no_longer_anchors_on_a_retired_row() -> None:
    anchors = candidate_anchors("income_tax", -0.03, 0.0)
    assert anchors
    assert not {a.policy_id for a in anchors} & retired_policy_ids()

    gate = build_capability_gate(
        policy_type="income_tax",
        rate_change=-0.03,
        income_threshold=0.0,
        engine_estimate_billions=3855.0,
        calibrated=False,
    )
    used = (gate["benchmark_interpolation"] or {}).get("anchors_used", [])
    assert not set(used) & retired_policy_ids()
    assert "illustrative_500k_2pp" not in {
        a["policy_id"] for a in gate["official_benchmark_anchors"]
    }
    # The old headline was +$600B: the retired +$400B row scaled by 3/2.
    assert gate["headline_estimate_billions"] != 600.0


def test_assistant_anchor_eligible_semantics_are_unchanged() -> None:
    """The existing per-record flag still excludes the older-vintage rows."""
    ineligible = {k for k, v in KNOWN_SCORES.items() if not v.assistant_anchor_eligible}
    assert ineligible
    for pt, rate, thr in _GRID:
        for anchor in candidate_anchors(pt, rate, thr):
            assert anchor.policy_id not in ineligible
