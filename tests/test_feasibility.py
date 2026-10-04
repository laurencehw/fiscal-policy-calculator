from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from fiscal_model.feasibility import (
    assess_model_pilot_comparison,
    audit_cps_microsim_readiness,
)


def test_audit_cps_microsim_readiness_reports_ready_dataset(tmp_path):
    raw_dir = tmp_path / "data" / "asecpub24csv"
    raw_dir.mkdir(parents=True)
    (raw_dir / "pppub24.csv").write_text("stub", encoding="utf-8")
    (raw_dir / "hhpub24.csv").write_text("stub", encoding="utf-8")
    archive_path = tmp_path / "data" / "asecpub24csv.zip"
    archive_path.write_text("zip", encoding="utf-8")

    microdata_path = tmp_path / "tax_microdata.csv"
    pd.DataFrame(
        [
            {
                "agi": 90_000,
                "wages": 80_000,
                "married": 1,
                "children": 1,
                "weight": 60_000_000,
                "age_head": 45,
            },
            {
                "agi": 90_000,
                "wages": 80_000,
                "married": 0,
                "children": 0,
                "weight": 60_000_000,
                "age_head": 38,
            },
        ]
    ).to_csv(microdata_path, index=False)

    audit = audit_cps_microsim_readiness(
        microdata_path=microdata_path,
        raw_data_dir=raw_dir,
        archive_path=archive_path,
    )

    assert audit.ready_for_spike is True
    assert audit.reproducible_from_repo_inputs is True
    assert audit.missing_required_columns == []
    assert audit.row_count == 2
    assert all(check.passed for check in audit.checks)
    assert "interest_income" in audit.optional_columns_missing


def test_audit_cps_microsim_readiness_flags_missing_required_columns(tmp_path):
    raw_dir = tmp_path / "data" / "asecpub24csv"
    raw_dir.mkdir(parents=True)
    microdata_path = tmp_path / "tax_microdata.csv"
    pd.DataFrame(
        [
            {
                "agi": 90_000,
                "wages": 80_000,
                "married": 1,
                "children": 1,
                "weight": 60_000_000,
            }
        ]
    ).to_csv(microdata_path, index=False)

    audit = audit_cps_microsim_readiness(
        microdata_path=microdata_path,
        raw_data_dir=raw_dir,
    )

    assert audit.ready_for_spike is False
    assert "age_head" in audit.missing_required_columns
    assert any("required columns" in warning for warning in audit.warnings)


def test_assess_model_pilot_comparison_blocks_implausible_gaps():
    bundle = SimpleNamespace(
        results=[
            SimpleNamespace(model_name="CBO-Style", ten_year_cost=-664.2, distributional=None),
            SimpleNamespace(model_name="TPC-Microsim Pilot", ten_year_cost=-55.2, distributional=object()),
            SimpleNamespace(model_name="PWBM-OLG Pilot", ten_year_cost=357_435.3, distributional=None),
        ],
        errors={},
        max_gap=358_099.5,
    )

    assessment = assess_model_pilot_comparison(bundle)

    assert assessment.ready_for_spike is False
    assert assessment.status == "blocked"
    assert assessment.max_abs_ten_year_cost == 357_435.3
    assert any("PWBM-OLG Pilot" in blocker for blocker in assessment.blockers)
    assert any("Max model gap" in blocker for blocker in assessment.blockers)


def test_assess_model_pilot_comparison_allows_sane_two_model_spike():
    bundle = SimpleNamespace(
        results=[
            SimpleNamespace(model_name="CBO-Style", ten_year_cost=-120.0, distributional=None),
            SimpleNamespace(model_name="TPC-Microsim Pilot", ten_year_cost=-90.0, distributional=object()),
        ],
        errors={},
        max_gap=30.0,
    )

    assessment = assess_model_pilot_comparison(bundle)

    assert assessment.ready_for_spike is True
    assert assessment.status == "ready"
    assert assessment.blockers == []



# --- A bundle with fewer than two results has no gap -----------------------
#
# Every CBO-only Explore preset (TCJA, estate, AMT, tariffs, ...) returns one
# result: TPC-Microsim honestly raises "not representable".  The assessment
# used to turn that into a *quality blocker*, which the Scoring Models tab
# rendered as "this multi-model comparison has implausible gaps" -- a gap
# claim about a bundle that contains no gap.  These tests pin the split
# between "nothing to compare" (coverage) and "the comparison is broken"
# (blockers).


def _single_result_bundle(*, error: str, kind: str | None):
    kinds = {} if kind is None else {"TPC-Microsim Pilot": kind}
    return SimpleNamespace(
        results=[
            SimpleNamespace(model_name="CBO-Style", ten_year_cost=4581.9, distributional=None),
        ],
        errors={"TPC-Microsim Pilot": error},
        error_kinds=kinds,
        max_gap=None,
    )


def test_single_engine_bundle_with_a_capability_skip_is_not_a_quality_blocker():
    bundle = _single_result_bundle(
        error="Full TCJA packages are multi-provision.", kind="not_representable"
    )

    assessment = assess_model_pilot_comparison(bundle)

    assert assessment.blockers == []
    assert assessment.comparable is False
    assert assessment.status == "insufficient_engines"
    # Still not a go for expanding the pilot -- but for the right reason.
    assert assessment.ready_for_spike is False
    assert any("Only 1 model result" in note for note in assessment.coverage_notes)
    assert any(
        "TPC-Microsim Pilot" in note and "multi-provision" in note
        for note in assessment.coverage_notes
    )
    assert not any("gap" in blocker.lower() for blocker in assessment.blockers)


def test_single_engine_bundle_with_a_hard_backend_failure_is_a_blocker_naming_it():
    bundle = _single_result_bundle(error="Missing microdata file", kind="error")

    assessment = assess_model_pilot_comparison(bundle)

    assert assessment.status == "blocked"
    assert assessment.blockers == ["TPC-Microsim Pilot failed: Missing microdata file"]
    assert not any("gap" in blocker.lower() for blocker in assessment.blockers)


def test_unclassified_errors_default_to_hard_failures():
    # A bundle that predates ``error_kinds`` must not have its failures
    # silently relabelled as honest capability skips.
    bundle = _single_result_bundle(error="boom", kind=None)
    del bundle.error_kinds

    assessment = assess_model_pilot_comparison(bundle)

    assert assessment.blockers == ["TPC-Microsim Pilot failed: boom"]


def test_gap_blocker_names_the_two_engines_and_their_estimates():
    bundle = SimpleNamespace(
        results=[
            SimpleNamespace(model_name="CBO-Style", ten_year_cost=-664.2, distributional=None),
            SimpleNamespace(model_name="TPC-Microsim Pilot", ten_year_cost=11_000.0, distributional=None),
        ],
        errors={},
        max_gap=11_664.2,
    )

    assessment = assess_model_pilot_comparison(bundle)

    gap_blockers = [b for b in assessment.blockers if "gap" in b.lower()]
    assert len(gap_blockers) == 1
    message = gap_blockers[0]
    assert "TPC-Microsim Pilot" in message and "CBO-Style" in message
    assert "11,000.0B" in message and "-664.2B" in message
    assert "11,664.2B" in message
    assert assessment.max_gap_models == ("TPC-Microsim Pilot", "CBO-Style")


def test_real_cbo_only_preset_has_no_quality_blocker():
    """The preset the Scoring Models tab opens on, through the real pilots."""
    from fiscal_model import FiscalPolicyScorer, PolicyType, TaxPolicy
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.models.comparison import (
        build_default_comparison_models,
        compare_policy_models,
    )
    from fiscal_model.ui.tabs.multi_model import _build_policy

    name = next(n for n in PRESET_POLICIES if n.startswith("🏛️ TCJA Full Extension"))
    policy = _build_policy(name, PRESET_POLICIES[name], TaxPolicy, PolicyType.INCOME_TAX, 2023)
    models = build_default_comparison_models(FiscalPolicyScorer, use_real_data=False)

    bundle = compare_policy_models(policy, models, continue_on_error=True)
    assessment = assess_model_pilot_comparison(bundle)

    assert [r.model_name for r in bundle.results] == ["CBO-Style"]
    assert bundle.error_kinds == {"TPC-Microsim Pilot": "not_representable"}
    assert assessment.blockers == []
    assert assessment.status == "insufficient_engines"
