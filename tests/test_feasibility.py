from __future__ import annotations

from pathlib import Path

import pandas as pd

from fiscal_model.feasibility import audit_cps_microsim_readiness


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

