"""
Build a CPS ASEC-backed tax-unit file for the microsimulation engine.

The earlier prototype aggregated whole households into one tax unit. This file
now uses the CPS family identifier, spouse pointers, and parent pointers to
construct explicit tax units with documented fallback rules.

Source data (owner Decision 4, plan §6)
---------------------------------------
The raw CPS ASEC person and household files are **fetched by script at build
time and never vendored**: ``scripts/fetch_cps_asec.py`` downloads the Census
archive to a cache outside the repository and verifies its SHA-256. Run

    python -m fiscal_model.microsim.data_builder --fetch

to fetch, verify, extract and rebuild in one step, or ``--data-dir DIR`` to
build from an extract you already have. Only the derived tax-unit file is
under version control, alongside a ``*.provenance.json`` sidecar recording the
archive digest and the builder that produced it. (The provenance is a sidecar
rather than a comment header inside the CSV because several callers read the
file with a bare ``pandas.read_csv``, which would choke on one.)

Dependent age bands
-------------------
``children`` is the under-17 headcount and is what the CTC's current-law
qualifying-child test needs. It is *not* the EITC's qualifying-child test
(under 19, or under 24 and a full-time student), and it cannot express the
ARP CTC's $3,600-under-6 / $3,000-ages-6-17 split or an age-17 expansion.
The builder therefore also emits five dependent age-band counts —
``dependents_under_6``, ``dependents_6_to_16``, ``dependents_age_17``,
``dependents_age_18`` and ``dependents_19_to_23_student`` — over the same
dependent set that ``dependent_count`` counts. Student status uses ``A_ENRLW``
(attending school last week; universe 16-24), the only school-enrollment
variable on the ASEC person file.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

import pandas as pd

PERSON_COLUMNS = [
    "PH_SEQ",
    "P_SEQ",
    "A_LINENO",
    "A_AGE",
    "A_MARITL",
    "A_SEX",
    "A_EXPRRP",
    "A_FAMREL",
    "A_FAMNUM",
    "PECOHAB",
    "A_SPOUSE",
    "PEPAR1",
    "PEPAR2",
    "WSAL_VAL",
    "INT_VAL",
    "DIV_VAL",
    "RNT_VAL",
    "SS_VAL",
    "UC_VAL",
    "CAP_VAL",
    "MARSUPWT",
    "TAX_INC",
    "A_CLSWKR",
    "PEDISEYE",
    "PEDISREM",
    "A_ENRLW",
]

HOUSEHOLD_COLUMNS = [
    "H_SEQ",
    "GESTFIPS",
    "HSUP_WGT",
    "H_NUMPER",
]

NUMERIC_DEFAULTS = {
    "A_AGE": 0,
    "A_MARITL": 6,
    "A_EXPRRP": 0,
    "A_FAMREL": 0,
    "A_FAMNUM": 0,
    "PECOHAB": -1,
    "A_SPOUSE": 0,
    "PEPAR1": -1,
    "PEPAR2": -1,
    "WSAL_VAL": 0.0,
    "INT_VAL": 0.0,
    "DIV_VAL": 0.0,
    "RNT_VAL": 0.0,
    "SS_VAL": 0.0,
    "UC_VAL": 0.0,
    "CAP_VAL": 0.0,
    "MARSUPWT": 0.0,
    "TAX_INC": 0.0,
    "A_ENRLW": 0,
    "GESTFIPS": pd.NA,
}

#: Census landing page for the 2024 ASEC public-use files.
ASEC_LANDING_PAGE = (
    "https://www.census.gov/data/datasets/2024/demo/cps/cps-asec-2024.html"
)


def _fetch_module():
    """Import ``scripts/fetch_cps_asec.py`` lazily.

    It lives in ``scripts/`` rather than the package because it is a build
    tool, not a runtime dependency: nothing an app user runs imports it.
    """
    import importlib.util

    path = Path(__file__).resolve().parents[2] / "scripts" / "fetch_cps_asec.py"
    spec = importlib.util.spec_from_file_location("fetch_cps_asec", path)
    if spec is None or spec.loader is None:  # pragma: no cover - packaging guard
        raise RuntimeError(f"Cannot load the CPS fetch script from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OUTPUT_COLUMNS = [
    "id",
    "household_id",
    "family_id",
    "tax_unit_index",
    "member_count",
    "dependent_count",
    "dependents_under_6",
    "dependents_6_to_16",
    "dependents_age_17",
    "dependents_age_18",
    "dependents_19_to_23_student",
    "weight",
    "wages",
    "interest_income",
    "dividend_income",
    "capital_gains",
    "investment_income",
    "social_security",
    "unemployment",
    "children",
    "married",
    "age_head",
    "state_fips",
    "source_taxable_income",
    "agi",
]


def _read_available_columns(path: Path, columns: list[str]) -> pd.DataFrame:
    header = pd.read_csv(path, nrows=0).columns.tolist()
    usecols = [column for column in columns if column in header]
    return pd.read_csv(path, usecols=usecols)


def _normalize_records(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column, default in NUMERIC_DEFAULTS.items():
        if column not in normalized.columns:
            normalized.loc[:, column] = default
        else:
            normalized.loc[:, column] = normalized[column].fillna(default)
    return normalized


def load_cps_asec_records(data_dir: str) -> pd.DataFrame:
    """Load and merge the person and household CPS ASEC files."""
    p_path = Path(data_dir) / "pppub24.csv"
    h_path = Path(data_dir) / "hhpub24.csv"

    print("1. Loading Person Record (pppub24.csv)...")
    df_p = _read_available_columns(p_path, PERSON_COLUMNS)
    print(f"   Loaded {len(df_p):,} person records.")

    print("2. Loading Household Record (hhpub24.csv)...")
    df_h = _read_available_columns(h_path, HOUSEHOLD_COLUMNS)
    print(f"   Loaded {len(df_h):,} household records.")

    print("3. Merging Households and Persons...")
    merged = df_p.merge(df_h, left_on="PH_SEQ", right_on="H_SEQ", how="left")
    return _normalize_records(merged)


def _is_married_spouse(row: pd.Series) -> bool:
    return int(row["A_MARITL"]) in (1, 2) and int(row["A_SPOUSE"]) > 0


def _is_anchor_adult(row: pd.Series) -> bool:
    return int(row["A_AGE"]) >= 19 or _is_married_spouse(row)


def _is_dependent_candidate(row: pd.Series) -> bool:
    age = int(row["A_AGE"])
    has_parent_pointer = int(row["PEPAR1"]) > 0 or int(row["PEPAR2"]) > 0
    return age < 19 or (age < 24 and has_parent_pointer)


#: ``A_ENRLW`` code for "attending school last week" (universe: ages 16-24).
ENROLLED_IN_SCHOOL = 1


def _is_student(row: pd.Series) -> bool:
    """Whether a person is recorded as attending school last week."""
    return int(row.get("A_ENRLW", 0) or 0) == ENROLLED_IN_SCHOOL


def _dependent_age_bands(dependents: pd.DataFrame) -> dict[str, int]:
    """Count a unit's dependents into the five bands the credit rules need.

    The bands are cut at the statutory boundaries, not at convenient ones:
    6 is the ARP CTC's higher-amount boundary, 17 is the current-law CTC
    qualifying age, 19 is the EITC qualifying-child age, and 24 is the EITC's
    student extension. ``dependents_19_to_23_student`` is restricted to
    dependents recorded as attending school, because the EITC's over-18 test
    requires full-time student status.

    The bands are counted over the *same* dependent set as ``dependent_count``
    so the two can be read together; they therefore need not sum to
    ``children`` (the under-17 headcount over all members, dependent or not).
    """
    if dependents.empty:
        return {
            "dependents_under_6": 0,
            "dependents_6_to_16": 0,
            "dependents_age_17": 0,
            "dependents_age_18": 0,
            "dependents_19_to_23_student": 0,
        }
    ages = dependents["A_AGE"].astype(int)
    students = dependents.apply(_is_student, axis=1)
    return {
        "dependents_under_6": int((ages < 6).sum()),
        "dependents_6_to_16": int(((ages >= 6) & (ages <= 16)).sum()),
        "dependents_age_17": int((ages == 17).sum()),
        "dependents_age_18": int((ages == 18).sum()),
        "dependents_19_to_23_student": int(
            ((ages >= 19) & (ages <= 23) & students).sum()
        ),
    }


def _parent_lines(row: pd.Series) -> list[int]:
    parent_lines = []
    for column in ("PEPAR1", "PEPAR2"):
        value = int(row[column])
        if value > 0:
            parent_lines.append(value)
    return parent_lines


def _build_anchor_units(group: pd.DataFrame) -> list[dict[str, object]]:
    line_map = {int(row["A_LINENO"]): row for _, row in group.iterrows()}
    adult_lines = [line for line, row in line_map.items() if _is_anchor_adult(row)]
    units: list[dict[str, object]] = []
    used_adults: set[int] = set()

    for line in sorted(adult_lines):
        if line in used_adults:
            continue
        row = line_map[line]
        spouse_line = int(row["A_SPOUSE"])

        members = [line]
        if (
            spouse_line in adult_lines
            and spouse_line not in used_adults
            and _is_married_spouse(row)
            and int(line_map[spouse_line]["A_MARITL"]) in (1, 2)
        ):
            members.append(spouse_line)

        used_adults.update(members)
        units.append(
            {
                "members": sorted(members),
                "anchor_line": min(members),
            }
        )

    if units:
        return units

    if group.empty:
        return []

    first_line = int(group["A_LINENO"].min())
    return [{"members": [first_line], "anchor_line": first_line}]


def _find_parent_unit(
    parent_lines: list[int],
    local_units: list[dict[str, object]],
    fallback_unit: dict[str, object] | None,
) -> dict[str, object] | None:
    for parent_line in parent_lines:
        for unit in local_units:
            if parent_line in unit["members"]:
                return unit
        if fallback_unit is not None and parent_line in fallback_unit["members"]:
            return fallback_unit
    return None


def _construct_group_units(
    group: pd.DataFrame,
    *,
    fallback_unit: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    local_units = _build_anchor_units(group)
    assigned = {member for unit in local_units for member in unit["members"]}
    primary_unit = fallback_unit or (local_units[0] if local_units else None)

    remaining = group[~group["A_LINENO"].isin(assigned)].sort_values("A_LINENO")
    for _, row in remaining.iterrows():
        line = int(row["A_LINENO"])
        if _is_dependent_candidate(row):
            parent_unit = _find_parent_unit(_parent_lines(row), local_units, fallback_unit)
            if parent_unit is not None:
                parent_unit["members"].append(line)
                continue
            if primary_unit is not None and int(row["A_AGE"]) < 19:
                primary_unit["members"].append(line)
                continue

        local_units.append({"members": [line], "anchor_line": line})

    for unit in local_units:
        unit["members"] = sorted(set(unit["members"]))

    return local_units


def construct_tax_units(records: pd.DataFrame) -> pd.DataFrame:
    """
    Convert CPS households into tax units.

    Construction rules:
    - split households by CPS family identifier where available
    - pair married spouses using the CPS spouse pointer
    - attach dependents using parent pointers when available
    - otherwise fall back to the primary family unit for minors
    - leave unrelated adults as separate tax units
    """

    output_rows: list[dict[str, object]] = []

    for household_id, household in records.groupby("PH_SEQ", sort=True):
        household = household.sort_values("A_LINENO")
        household_units: list[dict[str, object]] = []

        family_ids = sorted(int(value) for value in household["A_FAMNUM"].dropna().unique())
        positive_family_ids = [family_id for family_id in family_ids if family_id > 0]

        for family_id in positive_family_ids:
            family = household[household["A_FAMNUM"] == family_id]
            new_units = _construct_group_units(family)
            for unit in new_units:
                unit["family_id"] = family_id
            household_units.extend(new_units)

        primary_household_unit = household_units[0] if household_units else None
        nonfamily_group = household[household["A_FAMNUM"] == 0]
        if not nonfamily_group.empty:
            new_units = _construct_group_units(nonfamily_group, fallback_unit=primary_household_unit)
            for unit in new_units:
                unit["family_id"] = 0
            household_units.extend(new_units)

        household_units = sorted(household_units, key=lambda unit: int(unit["anchor_line"]))

        for tax_unit_index, unit in enumerate(household_units, start=1):
            members = household[household["A_LINENO"].isin(unit["members"])].sort_values("A_LINENO")
            head = members.iloc[0]
            adults = members[members.apply(_is_anchor_adult, axis=1)]
            weight_source = adults if not adults.empty else members

            children_under_17 = int((members["A_AGE"] < 17).sum())
            married = int(
                len(adults) >= 2 and any(_is_married_spouse(row) for _, row in adults.iterrows())
            )
            dependents = members[members.apply(_is_dependent_candidate, axis=1)]

            output_rows.append(
                {
                    "id": int(household_id) * 100 + tax_unit_index,
                    "household_id": int(household_id),
                    "family_id": int(unit["family_id"]),
                    "tax_unit_index": tax_unit_index,
                    "member_count": int(len(members)),
                    "dependent_count": int(len(dependents)),
                    **_dependent_age_bands(dependents),
                    "weight": float(weight_source["MARSUPWT"].mean() / 100.0),
                    "wages": float(members["WSAL_VAL"].sum()),
                    "interest_income": float(members["INT_VAL"].sum()),
                    "dividend_income": float(members["DIV_VAL"].sum()),
                    "capital_gains": float(members["CAP_VAL"].sum()),
                    "investment_income": float(
                        members["INT_VAL"].sum()
                        + members["DIV_VAL"].sum()
                        + members["CAP_VAL"].sum()
                    ),
                    "social_security": float(members["SS_VAL"].sum()),
                    "unemployment": float(members["UC_VAL"].sum()),
                    "children": children_under_17,
                    "married": married,
                    "age_head": int(head["A_AGE"]),
                    "state_fips": head.get("GESTFIPS", pd.NA),
                    "source_taxable_income": float(members["TAX_INC"].sum()),
                }
            )

    clean_df = pd.DataFrame(output_rows)
    clean_df = clean_df.assign(
        agi=(
            clean_df["wages"]
            + clean_df["interest_income"]
            + clean_df["dividend_income"]
            + clean_df["capital_gains"]
            + clean_df["unemployment"]
        )
    )
    return clean_df[OUTPUT_COLUMNS]


#: The dependent age bands that make up an EITC qualifying-child count:
#: under 19, or under 24 and a full-time student (IRC §32(c)(3)).
EITC_QUALIFYING_BANDS = (
    "dependents_under_6",
    "dependents_6_to_16",
    "dependents_age_17",
    "dependents_age_18",
    "dependents_19_to_23_student",
)


def _weighted_millions(clean_df: pd.DataFrame, columns: tuple[str, ...]) -> float:
    """Weighted sum of ``columns`` in millions, 0.0 when any is absent.

    Callers hand this function partial frames (the validation tests build one
    by hand), so a missing column means "not measured", not an error.
    """
    if clean_df.empty or any(column not in clean_df.columns for column in columns):
        return 0.0
    total = sum(clean_df[column] for column in columns)
    return float((total * clean_df["weight"]).sum() / 1e6)


def summarize_tax_units(clean_df: pd.DataFrame) -> dict[str, float]:
    """Return headline validation metrics for the built microdata file."""
    households = int(clean_df["household_id"].nunique()) if not clean_df.empty else 0
    return {
        "records_created": float(len(clean_df)),
        "unique_households": float(households),
        "avg_units_per_household": float(len(clean_df) / households) if households else 0.0,
        "weighted_tax_units": float(clean_df["weight"].sum()) if not clean_df.empty else 0.0,
        "weighted_wages_billions": (
            float((clean_df["wages"] * clean_df["weight"]).sum() / 1e9) if not clean_df.empty else 0.0
        ),
        "weighted_agi_billions": (
            float((clean_df["agi"] * clean_df["weight"]).sum() / 1e9) if not clean_df.empty else 0.0
        ),
        "weighted_children_millions": (
            float((clean_df["children"] * clean_df["weight"]).sum() / 1e6) if not clean_df.empty else 0.0
        ),
        "weighted_dependents_millions": _weighted_millions(
            clean_df, ("dependent_count",)
        ),
        "weighted_dependents_under_6_millions": _weighted_millions(
            clean_df, ("dependents_under_6",)
        ),
        "weighted_eitc_qualifying_children_millions": _weighted_millions(
            clean_df, EITC_QUALIFYING_BANDS
        ),
    }


def validate_tax_units(clean_df: pd.DataFrame) -> list[str]:
    """Return builder warnings for obviously implausible aggregate outcomes."""
    warnings: list[str] = []
    summary = summarize_tax_units(clean_df)

    if clean_df["id"].duplicated().any():
        warnings.append("Duplicate tax-unit IDs detected.")
    if (clean_df["weight"] <= 0).any():
        warnings.append("Non-positive tax-unit weights detected.")
    if summary["avg_units_per_household"] < 1.0 or summary["avg_units_per_household"] > 2.5:
        warnings.append("Average units per household fell outside the expected range.")
    if summary["weighted_tax_units"] < 50_000_000 or summary["weighted_tax_units"] > 200_000_000:
        warnings.append("Weighted tax units fell outside the expected range.")
    if summary["weighted_agi_billions"] < summary["weighted_wages_billions"]:
        warnings.append("Weighted AGI fell below weighted wages, which is unlikely.")

    return warnings


def write_provenance(
    output_path: Path,
    *,
    data_dir: str,
    summary: dict[str, float],
    warnings: list[str],
    archive_sha256: str | None = None,
) -> Path:
    """Write the sidecar recording where this microdata file came from.

    A JSON sidecar rather than a comment header inside the CSV: several
    callers read the file with a bare ``pandas.read_csv`` and a ``#`` line
    would break them.
    """
    sidecar = output_path.with_suffix(".provenance.json")
    fetch = _fetch_module()
    payload = {
        "built_on": date.today().isoformat(),
        "builder": "fiscal_model.microsim.data_builder",
        "source": (
            "U.S. Census Bureau, Current Population Survey, Annual Social and "
            "Economic Supplement (ASEC), March 2024, public-use microdata"
        ),
        "source_url": ASEC_LANDING_PAGE,
        "archive_url": fetch.ASEC_2024_URL,
        "archive_sha256": archive_sha256 or fetch.ASEC_2024_SHA256,
        "person_file": "pppub24.csv",
        "household_file": "hhpub24.csv",
        "output_columns": list(OUTPUT_COLUMNS),
        "summary": summary,
        "warnings": warnings,
        "note": (
            "The raw archive is fetched by scripts/fetch_cps_asec.py and is "
            "never vendored (owner Decision 4). Rebuild with "
            "`python -m fiscal_model.microsim.data_builder --fetch`. The "
            "extract directory is deliberately not recorded here: it is a "
            "machine-local cache path, not provenance."
        ),
    }
    del data_dir
    sidecar.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return sidecar


def build_tax_microdata(
    data_dir: str,
    output_file: str = "tax_microdata_2024.csv",
    output_dir: str | Path | None = None,
    *,
    archive_sha256: str | None = None,
) -> pd.DataFrame | None:
    """
    Ingest CPS ASEC 2024 CSV files and create a clean tax-unit microdata file.

    Args:
        data_dir: Path to directory containing pppub24.csv and hhpub24.csv
        output_file: Name of the output CSV file
        output_dir: Where to write it. Defaults to
            ``data_dir/../../fiscal_model/microsim`` so an in-tree
            ``data/asecpub24csv`` extract still writes to the package; pass it
            explicitly when building from a cache outside the repository.
        archive_sha256: Digest of the source archive, recorded in the sidecar.
    """
    print("--- CPS ASEC DATA BUILDER ---")
    print(f"Source: {data_dir}")

    try:
        records = load_cps_asec_records(data_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: Could not find files. {exc}")
        return None

    print("4. Constructing Tax Units (family + spouse + parent pointers)...")
    clean_df = construct_tax_units(records)

    summary = summarize_tax_units(clean_df)
    warnings = validate_tax_units(clean_df)

    if output_dir is None:
        output_dir = os.path.join(Path(data_dir).parent.parent, "fiscal_model", "microsim")
    output_path = Path(output_dir) / output_file
    print(f"5. Saving to {output_path}...")
    clean_df.to_csv(output_path, index=False)
    sidecar = write_provenance(
        output_path,
        data_dir=data_dir,
        summary=summary,
        warnings=warnings,
        archive_sha256=archive_sha256,
    )
    print(f"   Provenance written to {sidecar}")

    print("\n--- SUMMARY ---")
    print(f"Records Created: {int(summary['records_created']):,}")
    print(f"Unique Households: {int(summary['unique_households']):,}")
    print(f"Average Units per Household: {summary['avg_units_per_household']:.2f}")
    print(f"Weighted Tax Units: {summary['weighted_tax_units']:,.0f}")
    print(f"Total Weighted Wages: ${summary['weighted_wages_billions']:,.1f}B")
    print(f"Total Weighted AGI: ${summary['weighted_agi_billions']:,.1f}B")
    print(f"Weighted Children <17: {summary['weighted_children_millions']:,.1f}M")
    print(f"Weighted Dependents: {summary['weighted_dependents_millions']:,.1f}M")
    print(
        "Weighted Dependents <6: "
        f"{summary['weighted_dependents_under_6_millions']:,.1f}M"
    )
    print(
        "Weighted EITC qualifying children: "
        f"{summary['weighted_eitc_qualifying_children_millions']:,.1f}M"
    )
    for warning in warnings:
        print(f"WARNING: {warning}")
    print("Done.")

    return clean_df


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: fetch (optionally) and rebuild the tax-unit file."""
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Build the CPS ASEC tax-unit file.")
    parser.add_argument(
        "--fetch",
        action="store_true",
        help=(
            "Fetch and verify the Census archive first (owner Decision 4). "
            "Implies --data-dir <cache>/extracted."
        ),
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Directory holding pppub24.csv and hhpub24.csv.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Where to write the tax-unit CSV (default: the installed package).",
    )
    parser.add_argument("--output-file", default="tax_microdata_2024.csv")
    args = parser.parse_args(argv)

    archive_sha256 = None
    if args.fetch:
        fetch = _fetch_module()
        data_dir = str(fetch.ensure_cps_asec())
        archive_sha256 = fetch.ASEC_2024_SHA256
        output_dir = args.output_dir or str(Path(__file__).resolve().parent)
    else:
        data_dir = args.data_dir or str(project_root / "data" / "asecpub24csv")
        output_dir = args.output_dir
        if not Path(data_dir).exists():
            print(f"Data directory not found at {data_dir}")
            print(
                "Run `python -m fiscal_model.microsim.data_builder --fetch` to "
                "download it (148 MB, cached outside the repository), or pass "
                "--data-dir."
            )
            return 1

    result = build_tax_microdata(
        data_dir,
        output_file=args.output_file,
        output_dir=output_dir,
        archive_sha256=archive_sha256,
    )
    return 0 if result is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
