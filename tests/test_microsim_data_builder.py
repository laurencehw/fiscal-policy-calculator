from __future__ import annotations

from pathlib import Path

import pandas as pd

from fiscal_model.microsim.data_builder import build_tax_microdata


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


def test_build_tax_microdata_builds_expected_household_level_output(tmp_path, capsys):
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
                "A_AGE": 12,
                "A_MARITL": 6,
                "A_SEX": 2,
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

    assert "Loaded 2 person records." in output
    assert "Loaded 1 household records." in output
    assert "Records Created: 1" in output
    assert list(built.columns) == [
        "id",
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
        "agi",
    ]

    row = built.iloc[0]
    assert row["id"] == 100
    assert row["weight"] == 1.0
    assert row["wages"] == 100_000
    assert row["interest_income"] == 1_000
    assert row["dividend_income"] == 2_000
    assert row["capital_gains"] == 5_000
    assert row["children"] == 1
    assert row["married"] == 1
    assert row["age_head"] == 45
    assert row["agi"] == 108_000


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
