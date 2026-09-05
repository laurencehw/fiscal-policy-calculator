"""
The Ask capability gate: uncalibrated engine runs must answer with the
nearest validated benchmark, not with a raw number nobody has checked.

Acceptance criterion from ``planning/redesign/REDESIGN_PLAN.md`` §9.3: a
"score a 25% corporate rate" question comes back within ~2x of the
interpolated official anchors, and never 5x off.

Since the CBO Options battery landed (Phase B), a +4pp corporate request is
*bracketed* by two official scores -- CBO Option 64 at +1pp (-$136B) and
Treasury's 21%->28% at +7pp (-$1,347B) -- so rule 4 in
``fiscal_model/assistant/benchmarks`` interpolates between them (-$741B)
instead of scaling the single 28% anchor through the origin (-$770B). Two real
anchors bracketing the request is the better of the two rules, and the 4%
change leaves the §9.3 criterion comfortably satisfied.
"""

from __future__ import annotations

import pytest

from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.assistant.benchmarks import (
    DIVERGENCE_LIMIT,
    build_capability_gate,
    candidate_anchors,
    interpolate_from_anchors,
)
from fiscal_model.assistant.tools import AssistantTools
from fiscal_model.policies import PolicyType, SpendingPolicy, TaxPolicy
from fiscal_model.scoring import FiscalPolicyScorer

# Treasury FY2025 Green Book, corporate rate 21% -> 28%.
CORPORATE_28_OFFICIAL = -1347.0
# CBO, Options for Reducing the Deficit: 2025-2034, option 64: 21% -> 22%.
CORPORATE_22_OFFICIAL = -135.7
# Treasury FY2025 Green Book, "Increase the top marginal income tax rate for
# high-income earners" (report p. 242). The Wave 4 provenance lane moved this
# anchor from a rounded -$252.0B to the row Treasury actually prints,
# $245,924M; see ``validation/preregistered.py`` (biden_high_income_tax.v2).
BIDEN_TOP_RATE_OFFICIAL = -245.9
# +4pp is bracketed by the two, so the gate interpolates rather than scaling.
CORPORATE_25_ANCHORED = CORPORATE_22_OFFICIAL + (
    CORPORATE_28_OFFICIAL - CORPORATE_22_OFFICIAL
) * ((0.04 - 0.01) / (0.07 - 0.01))


@pytest.fixture(scope="module")
def tools() -> AssistantTools:
    scorer = FiscalPolicyScorer()
    return AssistantTools(
        scorer=scorer,
        baseline=scorer.baseline,
        cbo_score_map=CBO_SCORE_MAP,
        presets=PRESET_POLICIES,
        policy_types=PolicyType,
        tax_policy_cls=TaxPolicy,
        spending_policy_cls=SpendingPolicy,
    )


# ---------------------------------------------------------------------------
# Anchor selection and interpolation
# ---------------------------------------------------------------------------


class TestAnchorSelection:
    def test_corporate_increase_anchors_on_the_same_direction_score(self):
        anchors = candidate_anchors("corporate_tax", 0.04)
        assert anchors, "no corporate anchor found"
        # Ordered nearest-first on rate change: +1pp (CBO Option 64) then +7pp.
        assert anchors[0].policy_id == "cbo_opt64_corporate_rate_1pp"
        assert "biden_corporate_28" in {a.policy_id for a in anchors}
        # The 2017 cut runs off a 35% base; it must not be mixed in.
        assert all(a.rate_change > 0 for a in anchors)

    def test_corporate_cut_anchors_on_the_2017_cut(self):
        anchors = candidate_anchors("corporate_tax", -0.05)
        assert anchors[0].policy_id == "tcja_2017_corporate"

    def test_income_anchor_prefers_the_nearest_threshold(self):
        top_rate = candidate_anchors("income_tax", 0.05, 1_000_000)
        all_filers = candidate_anchors("income_tax", 0.01, 0)
        assert top_rate[0].income_threshold == 1_000_000
        assert all_filers[0].income_threshold == 0

    def test_unparameterised_family_has_no_anchor(self):
        assert candidate_anchors("estate_tax", 0.05) == []
        assert candidate_anchors("corporate_tax", 0.0) == []

    def test_interpolates_between_two_bracketing_anchors(self):
        anchors = candidate_anchors("corporate_tax", 0.04)
        interp = interpolate_from_anchors(anchors, 0.04)
        assert interp is not None
        assert interp["estimate_ten_year_billions"] == pytest.approx(
            CORPORATE_25_ANCHORED, abs=1.0
        )
        assert "linear interpolation" in interp["method"]
        assert set(interp["anchors_used"]) == {
            "cbo_opt64_corporate_rate_1pp",
            "biden_corporate_28",
        }

    def test_scaling_through_the_origin(self):
        """Outside the anchors' range there is nothing to interpolate between,
        so the nearest anchor is scaled through the origin."""
        anchors = candidate_anchors("corporate_tax", 0.10)
        interp = interpolate_from_anchors(anchors, 0.10)
        assert interp is not None
        assert interp["estimate_ten_year_billions"] == pytest.approx(
            CORPORATE_28_OFFICIAL * (0.10 / 0.07), abs=1.0
        )
        assert "scaling through the origin" in interp["method"]
        assert interp["anchors_used"] == ["biden_corporate_28"]


# ---------------------------------------------------------------------------
# Gate payload
# ---------------------------------------------------------------------------


class TestGatePayload:
    def test_uncalibrated_path_leads_with_the_anchor(self):
        gate = build_capability_gate(
            policy_type="income_tax",
            rate_change=0.026,
            income_threshold=400_000,
            engine_estimate_billions=-409.0,
            calibrated=False,
        )
        assert gate["estimate_basis"] == "official_benchmark_interpolation"
        assert gate["headline_estimate_billions"] == pytest.approx(BIDEN_TOP_RATE_OFFICIAL, abs=1.0)
        assert gate["uncalibrated_model_estimate_billions"] == -409.0
        assert gate["official_benchmark_anchors"]
        assert "uncalibrated model estimate" in gate["capability_note"]

    def test_calibrated_path_keeps_the_module_number_when_it_agrees(self):
        gate = build_capability_gate(
            policy_type="corporate_tax",
            rate_change=0.04,
            income_threshold=0.0,
            engine_estimate_billions=-798.4,
            calibrated=True,
        )
        assert gate["estimate_basis"] == "calibrated_module"
        assert gate["headline_estimate_billions"] == -798.4
        assert gate["engine_vs_anchor_ratio"] < DIVERGENCE_LIMIT

    def test_calibrated_path_defers_to_the_anchor_when_it_diverges(self):
        gate = build_capability_gate(
            policy_type="corporate_tax",
            rate_change=0.04,
            income_threshold=0.0,
            engine_estimate_billions=-4_100.0,  # the old, pre-fix behaviour
            calibrated=True,
        )
        assert gate["estimate_basis"] == "official_benchmark_interpolation"
        assert gate["headline_estimate_billions"] == pytest.approx(
            CORPORATE_25_ANCHORED, abs=1.0
        )
        assert "capability_warning" in gate

    def test_no_anchor_is_labelled_rather_than_invented(self):
        gate = build_capability_gate(
            policy_type="estate_tax",
            rate_change=0.05,
            income_threshold=0.0,
            engine_estimate_billions=-5_000.0,
            calibrated=False,
        )
        assert gate["estimate_basis"] == "uncalibrated_model_only"
        assert gate["official_benchmark_anchors"] == []
        assert gate["benchmark_interpolation"] is None
        assert "no official score" in gate["capability_note"].lower()


# ---------------------------------------------------------------------------
# Tool output shape (the contract the model sees)
# ---------------------------------------------------------------------------


class TestToolOutputShape:
    GATE_KEYS = (
        "estimate_basis",
        "headline_estimate_billions",
        "official_benchmark_anchors",
        "benchmark_interpolation",
        "capability_note",
        "raw_engine_estimate_billions",
    )

    def test_every_scored_hypothetical_carries_the_gate(self, tools):
        result = tools.dispatch(
            "score_hypothetical_policy",
            {
                "name": "Top rate +2pp above 400K",
                "policy_type": "income_tax",
                "rate_change": 0.02,
                "affected_income_threshold": 400_000,
            },
        )
        assert "error" not in result, result
        for key in self.GATE_KEYS:
            assert key in result, f"missing gate key {key!r}"
        assert result["ten_year_deficit_impact_billions"] == (
            result["headline_estimate_billions"]
        )

    def test_corporate_25_percent_is_within_2x_of_the_official_anchors(self, tools):
        """The §9.3 sanity case."""
        result = tools.dispatch(
            "score_hypothetical_policy",
            {
                "name": "Corporate rate to 25%",
                "policy_type": "corporate_tax",
                "rate_change": 0.04,
            },
        )
        assert "error" not in result, result

        headline = result["headline_estimate_billions"]
        anchored = result["benchmark_interpolation"]["estimate_ten_year_billions"]
        assert anchored == pytest.approx(CORPORATE_25_ANCHORED, abs=1.0)

        # Right direction (raises revenue -> reduces the deficit).
        assert headline < 0
        ratio = abs(headline / anchored)
        assert 1 / DIVERGENCE_LIMIT <= ratio <= DIVERGENCE_LIMIT, (
            f"headline ${headline:,.0f}B vs anchor ${anchored:,.0f}B (ratio {ratio:.2f})"
        )

        anchor_names = [a["name"] for a in result["official_benchmark_anchors"]]
        assert any("28%" in name for name in anchor_names), anchor_names

    def test_uncalibrated_income_path_quotes_the_treasury_anchor(self, tools):
        result = tools.dispatch(
            "score_hypothetical_policy",
            {
                "name": "Restore the 39.6% top rate",
                "policy_type": "income_tax",
                "rate_change": 0.026,
                "affected_income_threshold": 400_000,
            },
        )
        assert result["estimate_basis"] == "official_benchmark_interpolation"
        assert result["headline_estimate_billions"] == pytest.approx(BIDEN_TOP_RATE_OFFICIAL, abs=1.0)
        # The raw engine run is reported, but explicitly as uncalibrated.
        assert "uncalibrated_model_estimate_billions" in result
        assert result["raw_engine_estimate_billions"] != (
            result["headline_estimate_billions"]
        )
        assert "uncalibrated" in result["scoring_path"]

    def test_provenance_carries_citable_anchor_sources(self, tools):
        tools.reset_provenance()
        tools.dispatch(
            "score_hypothetical_policy",
            {
                "name": "Corporate rate to 25%",
                "policy_type": "corporate_tax",
                "rate_change": 0.04,
            },
        )
        sources = tools.provenance[-1]["sources"]
        assert sources, "no source records recorded for the scoring tool"
        assert any("Corporate" in record["title"] for record in sources)
        assert any(record["publisher"] for record in sources)
