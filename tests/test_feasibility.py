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

