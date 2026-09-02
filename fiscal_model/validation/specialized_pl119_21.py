"""
P.L. 119-21 provision-level validation runner (JCT line items).

Phase D, plan §4.3. This is the **first sourced line-item block** in the
calibrated tier. Every other calibrated target in the repository is either a
rounded headline figure or a model estimate; these targets are individual rows
of a published JCT table, transcribed with page references into
``fiscal_model/data_files/validation/pl119_21_jct_line_items.csv`` by
``scripts/extract_pl119_21_line_items.py``. Its ``--pdf`` mode re-checks every
printed total against the page the row records, **sign included**, so a revenue
loss transcribed as a raiser fails rather than passing on its digits; the one
derived total JCT never prints is reported as unverifiable there and is
cross-checked against JCT's own chapter subtotal instead.

Source
------
Joint Committee on Taxation, **JCX-35-25** (1 July 2025), estimated revenue
effects of the tax provisions in Title VII of the Senate substitute - the text
enacted as P.L. 119-21 - against a present-law baseline. CBO's companion
estimate of the same law (publication 61570, 21 July 2025) is scored against
CBO's **January 2025** baseline, which is the vintage these provisions are
scored on here.

What this measures, and what it does not
----------------------------------------
The app reproduces the *aggregate* TCJA-extension cost to 0.4% because
``TCJAExtensionPolicy`` carries a single calibration factor fitted to CBO's
$4.6T total. Nothing in the module is fitted to any individual JCT row. So each
entry here is an **uncalibrated reconstruction**: it asks whether a module tuned
on one aggregate can also decompose, and the honest answer is reported rather
than closed. Every entry therefore sets ``calibrated_to_target=False``, which
keeps it out of the fitted-calibrated mean in ``scripts/cold_holdout.py``.

Provisions the app cannot build - tips, overtime, car-loan interest, Trump
accounts, cost recovery, section 163(j), the international provisions, and every
energy-credit termination - are recorded ``out_of_scope`` in the CSV with the
reason, and are never scored. The energy terminations are excluded for
**leakage** rather than for a missing feature: the climate module's IRA-repeal
annual is documented as calibrated to reproduce the -$783B IRA-repeal target, so
routing an energy-credit repeal through it would score a constant against the
same reform that set it.

Sign convention: the CSV's ``deficit_effect_10yr_billions`` and
``ScoringResult.total_10_year_cost`` both use deficit effect (positive increases
the deficit), so targets and model output compare directly with no sign flip.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

from ..baseline import BaselineVintage
from .benchmark_sources import provenance_for
from .core import (
    ValidationResult,
    build_scorer_for_vintage,
    build_validation_result,
    calculate_percent_difference,
)

logger = logging.getLogger(__name__)

#: The transcribed JCT table.
LINE_ITEMS_CSV = (
    Path(__file__).resolve().parent.parent
    / "data_files"
    / "validation"
    / "pl119_21_jct_line_items.csv"
)

#: The baseline CBO's own estimate of P.L. 119-21 is measured against
#: (publication 61570). Phase D replaced the interpolated January 2025 vintage
#: with figures transcribed from publication 61172 so this is a real choice
#: rather than a label.
PL119_21_VINTAGE = BaselineVintage.CBO_JAN_2025

#: The fiscal year JCX-35-25's own window opens on. The scorer's baseline window
#: is what the model sums over, so it must be JCT's window - **FY2025-2034** -
#: and not the year the provisions take effect. Getting this wrong silently
#: replaces JCT's zero-effect 2025 column with a tenth year of effect in 2035.
_SCORER_START_YEAR = 2025

#: The year the provisions themselves take effect. P.L. 119-21's individual
#: provisions are generally effective for tax years beginning after 31 December
#: 2025, so the policy is built with ``start_year=2026`` and
#: ``Policy.is_active()`` leaves FY2025 at zero inside the FY2025-2034 window -
#: which is exactly what JCT prints for most of these rows.
_POLICY_EFFECTIVE_YEAR = 2026

PL119_21_BENCHMARK_KIND = "Sourced line item (JCX-35-25)"

#: Provision id -> the single ``create_tcja_extension`` flag that builds it.
#: Deliberately a lookup rather than an ``eval`` of the CSV's ``module_path``:
#: the CSV records what the mapping *is* for a reader, this dict is what the
#: code executes, and :func:`_assert_mapping_matches_csv` fails loudly if the
#: two ever drift apart.
_TCJA_COMPONENT_FLAG: dict[str, str] = {
    "pl119_21_rate_extension": "extend_rate_cuts",
    "pl119_21_standard_deduction": "extend_standard_deduction",
    "pl119_21_personal_exemption_termination": "keep_exemption_elimination",
    "pl119_21_child_tax_credit": "extend_ctc",
    "pl119_21_qbi_199a": "extend_passthrough",
    "pl119_21_estate_gift_exemption": "extend_estate",
    "pl119_21_amt_exemption": "extend_amt",
    "pl119_21_salt_cap_40k": "keep_salt_cap",
}

#: Every flag ``create_tcja_extension`` accepts, so a single-component policy can
#: be built by switching all of them off and one back on.
_ALL_TCJA_FLAGS: tuple[str, ...] = (
    "extend_rate_cuts",
    "extend_standard_deduction",
    "keep_exemption_elimination",
    "extend_passthrough",
    "extend_ctc",
    "extend_estate",
    "extend_amt",
    "keep_salt_cap",
)

#: Per-provision structural caveats. These are statements about the module, not
#: excuses: each names the specific reason the component cannot be expected to
#: land on its JCT row.
_LIMITATIONS: dict[str, list[str]] = {
    "pl119_21_rate_extension": [
        "The module's rate-cut component carries one hard-coded aggregate cost "
        "grown at 3.5%/yr, with no bracket structure; JCT's row reflects the "
        "actual 2026 schedule reversion bracket by bracket.",
    ],
    "pl119_21_standard_deduction": [
        "The standard-deduction component is a single national annual cost, so "
        "it cannot reflect P.L. 119-21's enhancement above a straight TCJA "
        "extension.",
    ],
    "pl119_21_personal_exemption_termination": [
        "P.L. 119-21 pairs the permanent repeal of personal exemptions with a new "
        "temporary senior deduction, and JCT nets the two in this single row; the "
        "module's offset represents the repeal alone.",
    ],
    "pl119_21_child_tax_credit": [
        "The module's CTC component represents the $2,000 TCJA credit; P.L. "
        "119-21 sets $2,200 and indexes it, which the fixed annual cannot track.",
    ],
    "pl119_21_qbi_199a": [
        "Section 199A is modelled as one aggregate annual cost growing at 4%/yr, "
        "with no pass-through income distribution and no phase-in thresholds.",
    ],
    "pl119_21_estate_gift_exemption": [
        "The estate component is an aggregate annual cost, not the exemption/rate "
        "machinery in estate.py, so it cannot represent the move to a $15M "
        "exemption specifically.",
    ],
    "pl119_21_amt_exemption": [
        "The AMT component is a single aggregate; P.L. 119-21 also lowers the "
        "phaseout thresholds and raises the phaseout rate, which raises revenue "
        "relative to a plain extension and the module has no way to represent.",
    ],
    "pl119_21_salt_cap_40k": [
        "DESIGN MISMATCH, stated rather than tuned away. P.L. 119-21 raises the "
        "SALT cap to $40,000 with a phase-down above $500,000 of income and a "
        "reversion to $10,000 after 2029; the module's SALT component represents "
        "the flat $10,000 cap, which raises far more revenue. This row is the "
        "largest error in the block and the reason is structural, not calibration.",
    ],
}


@dataclass(frozen=True)
class PL11921LineItem:
    """One row of the transcribed JCX-35-25 table."""

    provision_id: str
    chapter: str
    jct_item: str
    provision: str
    effective: str
    pdf_page: int
    revenue_effect_2025_34_millions: int
    deficit_effect_10yr_billions: float
    mapping_status: str
    module_path: str
    is_reference_row: bool
    extracted_by: str
    note: str


def _read_rows(path: Path) -> list[PL11921LineItem]:
    if not path.exists():
        logger.warning("P.L. 119-21 line-item CSV not found at %s", path)
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        lines = [line for line in handle if not line.startswith("#")]
    reader = csv.DictReader(lines)
    items: list[PL11921LineItem] = []
    for row in reader:
        items.append(
            PL11921LineItem(
                provision_id=row["provision_id"],
                chapter=row["chapter"],
                jct_item=row["jct_item"],
                provision=row["provision"],
                effective=row["effective"],
                pdf_page=int(row["pdf_page"]),
                revenue_effect_2025_34_millions=int(
                    row["revenue_effect_2025_34_millions"]
                ),
                deficit_effect_10yr_billions=float(
                    row["deficit_effect_10yr_billions"]
                ),
                mapping_status=row["mapping_status"],
                module_path=row["module_path"],
                is_reference_row=row["is_reference_row"] == "true",
                extracted_by=row["extracted_by"],
                note=row["note"],
            )
        )
    return items


#: Loaded once at import, like the CBO options battery.
PL119_21_LINE_ITEMS: tuple[PL11921LineItem, ...] = tuple(_read_rows(LINE_ITEMS_CSV))


def mapped_line_items() -> list[PL11921LineItem]:
    """Rows the app can actually build a policy for."""
    return [
        item
        for item in PL119_21_LINE_ITEMS
        if item.mapping_status == "mapped" and not item.is_reference_row
    ]


def out_of_scope_line_items() -> list[PL11921LineItem]:
    """Rows recorded with a reason and deliberately never scored."""
    return [
        item for item in PL119_21_LINE_ITEMS if item.mapping_status == "out_of_scope"
    ]


def reference_line_items() -> list[PL11921LineItem]:
    """Chapter subtotals and the net total, transcribed for cross-checking."""
    return [item for item in PL119_21_LINE_ITEMS if item.mapping_status == "reference"]


def describe_line_item_coverage() -> dict[str, object]:
    """Account for every transcribed row, so none is silently dropped."""
    mapped = mapped_line_items()
    out_of_scope = out_of_scope_line_items()
    reference = reference_line_items()
    accounted = {
        item.provision_id for item in (*mapped, *out_of_scope, *reference)
    }
    return {
        "total": len(PL119_21_LINE_ITEMS),
        "mapped": sorted(item.provision_id for item in mapped),
        "out_of_scope": sorted(item.provision_id for item in out_of_scope),
        "reference": sorted(item.provision_id for item in reference),
        "unaccounted": sorted(
            {item.provision_id for item in PL119_21_LINE_ITEMS} - accounted
        ),
    }


def _assert_mapping_matches_csv() -> list[str]:
    """Return every disagreement between the CSV and :data:`_TCJA_COMPONENT_FLAG`."""
    problems: list[str] = []
    for item in mapped_line_items():
        flag = _TCJA_COMPONENT_FLAG.get(item.provision_id)
        if flag is None:
            problems.append(
                f"{item.provision_id} is 'mapped' in the CSV but has no runner "
                "mapping"
            )
            continue
        if f"{flag}=True" not in item.module_path:
            problems.append(
                f"{item.provision_id}: CSV module_path {item.module_path!r} does "
                f"not name the flag the runner uses ({flag})"
            )
    for provision_id in _TCJA_COMPONENT_FLAG:
        if provision_id not in {item.provision_id for item in mapped_line_items()}:
            problems.append(
                f"{provision_id} has a runner mapping but is not 'mapped' in the CSV"
            )
    return problems


def build_provision_policy(provision_id: str):
    """Build the single-component TCJA policy a mapped line item describes."""
    flag = _TCJA_COMPONENT_FLAG.get(provision_id)
    if flag is None:
        raise ValueError(f"No module path for P.L. 119-21 provision {provision_id!r}")

    from ..tcja import create_tcja_extension

    kwargs = {name: False for name in _ALL_TCJA_FLAGS}
    kwargs[flag] = True
    policy = create_tcja_extension(
        extend_all=False, start_year=_POLICY_EFFECTIVE_YEAR, **kwargs
    )
    policy.name = f"P.L. 119-21: {provision_id}"
    return policy


def validate_pl119_21_provision(
    provision_id: str, verbose: bool = True
) -> ValidationResult:
    """Score one mapped provision against its JCT line item."""
    by_id = {item.provision_id: item for item in PL119_21_LINE_ITEMS}
    if provision_id not in by_id:
        raise ValueError(
            f"Unknown P.L. 119-21 provision: {provision_id}. "
            f"Available: {sorted(item.provision_id for item in mapped_line_items())}"
        )
    item = by_id[provision_id]
    if item.mapping_status != "mapped":
        raise ValueError(
            f"{provision_id} is {item.mapping_status!r}, not 'mapped'; it has no "
            "module path and must not be scored."
        )

    policy = build_provision_policy(provision_id)
    # Baseline window = JCT's window (FY2025-2034); policy effect starts 2026.
    scorer = build_scorer_for_vintage(
        PL119_21_VINTAGE, start_year=_SCORER_START_YEAR, use_real_data=False
    )
    result = scorer.score_policy(policy, dynamic=False)

    validation_result = build_validation_result(
        policy_id=provision_id,
        policy_name=f"P.L. 119-21: {item.provision}",
        official_10yr=item.deficit_effect_10yr_billions,
        official_source="Joint Committee on Taxation",
        model_10yr=result.total_10_year_cost,
        model_first_year=result.final_deficit_effect[0],
        model_parameters={
            # Provenance is not restated here. ``benchmark_sources.py`` is the
            # single authority on where a target came from, and it carries a
            # transcribed record for every row of this block; a runner that
            # asserted its own label could only ever disagree with it.
            "provenance": provenance_for(provision_id),
            # No module constant is fitted to any individual JCT row - the TCJA
            # calibration factor is fitted to CBO's $4.6T aggregate - so a miss
            # here is a finding about the decomposition, not a regression.
            "calibrated_to_target": False,
            "jct_document": "JCX-35-25",
            "jct_item": item.jct_item,
            "jct_pdf_page": item.pdf_page,
            "module_path": item.module_path,
            "scoring_vintage": PL119_21_VINTAGE.value,
            "scoring_window": f"FY{_SCORER_START_YEAR}-{_SCORER_START_YEAR + 9}",
            "policy_effective_year": _POLICY_EFFECTIVE_YEAR,
        },
        notes=item.note,
        benchmark_date="2025-07",
        benchmark_url="https://www.jct.gov/publications/2025/jcx-35-25/",
        benchmark_kind=PL119_21_BENCHMARK_KIND,
        known_limitations=_LIMITATIONS.get(provision_id),
    )

    if verbose:
        print(f"\n{'=' * 70}")
        print(f"P.L. 119-21 line item: {item.provision}")
        print(f"{'=' * 70}")
        print(f"JCX-35-25 item {item.jct_item} (PDF p. {item.pdf_page})")
        print(
            f"JCT: {item.revenue_effect_2025_34_millions:+,}M revenue "
            f"= ${item.deficit_effect_10yr_billions:+,.1f}B deficit"
        )
        print(f"Model estimate: ${validation_result.model_10yr:+,.1f}B")
        print(
            f"Difference: ${validation_result.difference:+,.1f}B "
            f"({validation_result.percent_difference:+.1f}%)"
        )
        print(f"Rating: {validation_result.accuracy_rating}")
        print("Note: no module constant is fitted to this row.")
        for limitation in validation_result.known_limitations:
            print(f"  - {limitation}")

    return validation_result


def _error_result(item: PL11921LineItem, exc: Exception) -> ValidationResult:
    """Placeholder row for a provision that failed to score.

    A zero model score against a non-zero target is a 100% miss, not a perfect
    match; reporting 0.0 would let a broken runner sit inside every accuracy
    band.
    """
    official = item.deficit_effect_10yr_billions
    return ValidationResult(
        policy_id=item.provision_id,
        policy_name=f"P.L. 119-21: {item.provision}",
        official_10yr=official,
        official_source="Joint Committee on Taxation",
        model_10yr=0.0,
        model_first_year=0.0,
        difference=-official,
        percent_difference=calculate_percent_difference(0.0, official),
        direction_match=False,
        accuracy_rating="Error",
        model_parameters={
            "provenance": provenance_for(item.provision_id),
            "calibrated_to_target": False,
        },
        notes=f"Model error: {exc!s}",
        benchmark_kind=PL119_21_BENCHMARK_KIND,
        benchmark_date="2025-07",
        benchmark_url="https://www.jct.gov/publications/2025/jcx-35-25/",
        known_limitations=["Model execution failed during this validation run."],
    )


def validate_all_pl119_21(verbose: bool = True) -> list[ValidationResult]:
    """Score every mapped P.L. 119-21 line item."""
    mismatches = _assert_mapping_matches_csv()
    if mismatches:
        raise AssertionError(
            "P.L. 119-21 CSV and runner mapping disagree:\n  - "
            + "\n  - ".join(mismatches)
        )

    if verbose:
        print("\n" + "=" * 70)
        print("P.L. 119-21 PROVISION-LEVEL VALIDATION (JCX-35-25 line items)")
        print("=" * 70)

    results: list[ValidationResult] = []
    for item in mapped_line_items():
        try:
            results.append(
                validate_pl119_21_provision(item.provision_id, verbose=verbose)
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("P.L. 119-21 provision failed: %s", item.provision_id)
            results.append(_error_result(item, exc))

    if verbose and results:
        errors = [abs(r.percent_difference) for r in results]
        print("\n" + "-" * 70)
        print(
            f"{len(results)} sourced line items | mean abs error "
            f"{sum(errors) / len(errors):.1f}% | within 15%: "
            f"{sum(1 for e in errors if e <= 15.0)}/{len(results)}"
        )
        out_of_scope = out_of_scope_line_items()
        print(
            f"{len(out_of_scope)} further provisions recorded out of scope with a "
            "reason and not scored."
        )
        print(
            "These are uncalibrated reconstructions: the module's calibration "
            "factor is\nfitted to CBO's $4.6T aggregate, not to any JCT row."
        )

    return results


__all__ = [
    "PL119_21_LINE_ITEMS",
    "PL119_21_VINTAGE",
    "PL11921LineItem",
    "build_provision_policy",
    "describe_line_item_coverage",
    "mapped_line_items",
    "out_of_scope_line_items",
    "reference_line_items",
    "validate_all_pl119_21",
    "validate_pl119_21_provision",
]
