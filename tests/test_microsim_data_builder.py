from __future__ import annotations

from pathlib import Path

import pandas as pd

from fiscal_model.microsim.data_builder import (
    build_tax_microdata,
    summarize_tax_units,
    validate_tax_units,
)


def _make_project_dirs(tmp_path: Path) -> tuple[Path, Path]:
    project_root = tmp_path / "project"
    data_dir = project_root / "data" / "asecpub24csv"
    output_dir = project_root / "fiscal_model" / "microsim"
    data_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    return data_dir, output_dir


def test_build_tax_microdata_handles_missing_source_files(tmp_path, capsys):
    missing_dir = tmp_path / "does-not-exist"

    build_tax_microdata(str(missing_dir), output_file="ignored.csv")
    output = capsys.readouterr().out

    assert "ERROR: Could not find files." in output


def test_build_tax_microdata_builds_expected_tax_unit_output(tmp_path, capsys):
    data_dir, output_dir = _make_project_dirs(tmp_path)

    pd.DataFrame(
        [
            {
                "PH_SEQ": 100,
                "P_SEQ": 1,
                "A_LINENO": 1,
                "A_AGE": 45,
                "A_MARITL": 1,
                "A_SEX": 1,
                "A_EXPRRP": 1,
                "A_FAMREL": 1,
                "A_FAMNUM": 1,
                "PECOHAB": -1,
                "A_SPOUSE": 2,
                "PEPAR1": -1,
                "PEPAR2": -1,
                "WSAL_VAL": 100_000,
                "INT_VAL": 1_000,
                "DIV_VAL": 2_000,
                "RNT_VAL": 0,
                "SS_VAL": 0,
                "UC_VAL": 0,
                "CAP_VAL": 5_000,
                "MARSUPWT": 120.0,
                "TAX_INC": 108_000,
                "A_CLSWKR": 1,
                "PEDISEYE": 0,
                "PEDISREM": 0,
            },
            {
                "PH_SEQ": 100,
                "P_SEQ": 2,
                "A_LINENO": 2,
                "A_AGE": 43,
                "A_MARITL": 1,
                "A_SEX": 2,
                "A_EXPRRP": 3,
                "A_FAMREL": 2,
                "A_FAMNUM": 1,
                "PECOHAB": -1,
                "A_SPOUSE": 1,
                "PEPAR1": -1,
                "PEPAR2": -1,
                "WSAL_VAL": 20_000,
                "INT_VAL": 200,
                "DIV_VAL": 300,
                "RNT_VAL": 0,
                "SS_VAL": 0,
                "UC_VAL": 0,
                "CAP_VAL": 0,
                "MARSUPWT": 100.0,
                "TAX_INC": 20_500,
                "A_CLSWKR": 1,
                "PEDISEYE": 0,
                "PEDISREM": 0,
            },
            {
                "PH_SEQ": 100,
                "P_SEQ": 3,
                "A_LINENO": 3,
                "A_AGE": 12,
                "A_MARITL": 6,
                "A_SEX": 2,
                "A_EXPRRP": 5,
                "A_FAMREL": 3,
                "A_FAMNUM": 1,
                "PECOHAB": -1,
                "A_SPOUSE": 0,
                "PEPAR1": 1,
                "PEPAR2": -1,
                "WSAL_VAL": 0,
                "INT_VAL": 0,
                "DIV_VAL": 0,
                "RNT_VAL": 0,
                "SS_VAL": 0,
                "UC_VAL": 0,
                "CAP_VAL": 0,
                "MARSUPWT": 80.0,
                "TAX_INC": 0,
                "A_CLSWKR": 0,
                "PEDISEYE": 0,
                "PEDISREM": 0,
            },
        ]
    ).to_csv(data_dir / "pppub24.csv", index=False)
    pd.DataFrame(
        [
            {
                "H_SEQ": 100,
                "GESTFIPS": 6,
                "HSUP_WGT": 50.0,
                "H_NUMPER": 2,
            }
        ]
    ).to_csv(data_dir / "hhpub24.csv", index=False)

    build_tax_microdata(str(data_dir), output_file="built.csv")
    output = capsys.readouterr().out
    built = pd.read_csv(output_dir / "built.csv")

    assert "Loaded 3 person records." in output
    assert "Loaded 1 household records." in output
    assert "Records Created: 1" in output
    assert "Average Units per Household: 1.00" in output
    assert set(
        [
            "id",
            "household_id",
            "family_id",
            "tax_unit_index",
            "member_count",
            "dependent_count",
            "weight",
            "wages",
            "interest_income",
            "dividend_income",
            "capital_gains",
            "social_security",
            "unemployment",
            "children",
            "married",
            "age_head",
            "state_fips",
            "source_taxable_income",
            "agi",
        ]
    ).issubset(built.columns)

    row = built.iloc[0]
    assert row["id"] == 10001
    assert row["household_id"] == 100
    assert row["family_id"] == 1
    assert row["member_count"] == 3
    assert row["dependent_count"] == 1
    assert row["weight"] == 1.1
    assert row["wages"] == 120_000
    assert row["interest_income"] == 1_200
    assert row["dividend_income"] == 2_300
    assert row["capital_gains"] == 5_000
    assert row["children"] == 1
    assert row["married"] == 1
    assert row["age_head"] == 45
    assert row["agi"] == 128_500


def test_build_tax_microdata_defaults_optional_income_fields_to_zero(tmp_path):
    data_dir, output_dir = _make_project_dirs(tmp_path)

    pd.DataFrame(
        [
            {
                "PH_SEQ": 200,
                "P_SEQ": 1,
                "A_LINENO": 1,
                "A_AGE": 35,
                "A_MARITL": 6,
                "A_SEX": 1,
                "A_EXPRRP": 1,
                "A_FAMREL": 1,
                "A_FAMNUM": 1,
                "PECOHAB": -1,
                "A_SPOUSE": 0,
                "PEPAR1": -1,
                "PEPAR2": -1,
                "WSAL_VAL": 50_000,
                "INT_VAL": 500,
                "DIV_VAL": 250,
                "RNT_VAL": 100,
                "SS_VAL": 0,
                "UC_VAL": 200,
                "MARSUPWT": 150.0,
                "A_CLSWKR": 1,
                "PEDISEYE": 0,
                "PEDISREM": 0,
            }
        ]
    ).to_csv(data_dir / "pppub24.csv", index=False)
    pd.DataFrame(
        [
            {
                "H_SEQ": 200,
                "GESTFIPS": 36,
                "HSUP_WGT": 70.0,
                "H_NUMPER": 1,
            }
        ]
    ).to_csv(data_dir / "hhpub24.csv", index=False)

    build_tax_microdata(str(data_dir), output_file="no_capital_gains.csv")
    built = pd.read_csv(output_dir / "no_capital_gains.csv")

    row = built.iloc[0]
    assert row["capital_gains"] == 0
    assert row["married"] == 0
    assert row["children"] == 0
    assert row["agi"] == 50_950


def test_build_tax_microdata_splits_unrelated_adults_into_separate_units(tmp_path):
    data_dir, output_dir = _make_project_dirs(tmp_path)

    pd.DataFrame(
        [
            {
                "PH_SEQ": 300,
                "P_SEQ": 1,
                "A_LINENO": 1,
                "A_AGE": 40,
                "A_MARITL": 6,
                "A_SEX": 1,
                "A_EXPRRP": 1,
                "A_FAMREL": 1,
                "A_FAMNUM": 1,
                "PECOHAB": -1,
                "A_SPOUSE": 0,
                "PEPAR1": -1,
                "PEPAR2": -1,
                "WSAL_VAL": 80_000,
                "INT_VAL": 200,
                "DIV_VAL": 0,
                "RNT_VAL": 0,
                "SS_VAL": 0,
                "UC_VAL": 0,
                "CAP_VAL": 0,
                "MARSUPWT": 120.0,
                "TAX_INC": 80_200,
                "A_CLSWKR": 1,
                "PEDISEYE": 0,
                "PEDISREM": 0,
            },
            {
                "PH_SEQ": 300,
                "P_SEQ": 2,
                "A_LINENO": 2,
                "A_AGE": 16,
                "A_MARITL": 7,
                "A_SEX": 2,
                "A_EXPRRP": 5,
                "A_FAMREL": 3,
                "A_FAMNUM": 1,
                "PECOHAB": -1,
                "A_SPOUSE": 0,
                "PEPAR1": 1,
                "PEPAR2": -1,
                "WSAL_VAL": 0,
                "INT_VAL": 0,
                "DIV_VAL": 0,
                "RNT_VAL": 0,
                "SS_VAL": 0,
                "UC_VAL": 0,
                "CAP_VAL": 0,
                "MARSUPWT": 120.0,
                "TAX_INC": 0,
                "A_CLSWKR": 0,
                "PEDISEYE": 0,
                "PEDISREM": 0,
            },
            {
                "PH_SEQ": 300,
                "P_SEQ": 3,
                "A_LINENO": 3,
                "A_AGE": 28,
                "A_MARITL": 6,
                "A_SEX": 1,
                "A_EXPRRP": 12,
                "A_FAMREL": 0,
                "A_FAMNUM": 0,
                "PECOHAB": -1,
                "A_SPOUSE": 0,
                "PEPAR1": -1,
                "PEPAR2": -1,
                "WSAL_VAL": 50_000,
                "INT_VAL": 100,
                "DIV_VAL": 0,
                "RNT_VAL": 0,
                "SS_VAL": 0,
                "UC_VAL": 0,
                "CAP_VAL": 0,
                "MARSUPWT": 80.0,
                "TAX_INC": 50_100,
                "A_CLSWKR": 1,
                "PEDISEYE": 0,
                "PEDISREM": 0,
            },
        ]
    ).to_csv(data_dir / "pppub24.csv", index=False)
    pd.DataFrame(
        [
            {
                "H_SEQ": 300,
                "GESTFIPS": 12,
                "HSUP_WGT": 90.0,
                "H_NUMPER": 3,
            }
        ]
    ).to_csv(data_dir / "hhpub24.csv", index=False)

    built = build_tax_microdata(str(data_dir), output_file="split_units.csv")
    saved = pd.read_csv(output_dir / "split_units.csv")

    assert len(built) == 2
    assert len(saved) == 2
    assert sorted(saved["member_count"].tolist()) == [1, 2]
    assert sorted(saved["weight"].tolist()) == [0.8, 1.2]
    assert saved["children"].sum() == 1


def test_tax_unit_summary_and_validation_report_implausible_values():
    clean_df = pd.DataFrame(
        [
            {
                "id": 1,
                "household_id": 1,
                "family_id": 1,
                "tax_unit_index": 1,
                "member_count": 1,
                "dependent_count": 0,
                "weight": -1.0,
                "wages": 10_000,
                "interest_income": 0,
                "dividend_income": 0,
                "capital_gains": 0,
                "social_security": 0,
                "unemployment": 0,
                "children": 0,
                "married": 0,
                "age_head": 30,
                "state_fips": 1,
                "source_taxable_income": 10_000,
                "agi": 10_000,
            },
            {
                "id": 1,
                "household_id": 1,
                "family_id": 0,
                "tax_unit_index": 2,
                "member_count": 1,
                "dependent_count": 0,
                "weight": -1.0,
                "wages": 20_000,
                "interest_income": 0,
                "dividend_income": 0,
                "capital_gains": 0,
                "social_security": 0,
                "unemployment": 0,
                "children": 0,
                "married": 0,
                "age_head": 40,
                "state_fips": 1,
                "source_taxable_income": 20_000,
                "agi": 20_000,
            },
        ]
    )

    summary = summarize_tax_units(clean_df)
    warnings = validate_tax_units(clean_df)

    assert summary["records_created"] == 2
    assert summary["avg_units_per_household"] == 2.0
    assert "Duplicate tax-unit IDs detected." in warnings
    assert "Non-positive tax-unit weights detected." in warnings
