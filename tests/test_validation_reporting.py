"""
Focused tests for validation result metadata and markdown reporting.
"""

from fiscal_model.validation.core import ValidationResult, build_validation_result
from fiscal_model.validation.reporting import generate_validation_report


def test_build_validation_result_infers_benchmark_metadata_and_limitations():
    result = build_validation_result(
        policy_id="ss_donut_250k",
        policy_name="SS tax on wages above $250K",
        official_10yr=-2700.0,
        official_source="Social Security Trustees",
        model_10yr=-2371.0,
        model_first_year=-210.0,
        notes="Donut hole benchmark from Trustees-style scoring.",
    )

    assert result.benchmark_kind == "Published actuarial estimate"
    assert result.needs_follow_up is True
    assert any("SSA earnings records" in limitation for limitation in result.known_limitations)


def test_generate_validation_report_surfaces_manuscript_sections():
    results = [
        ValidationResult(
            policy_id="biden_highincome_400k",
            policy_name="Biden High-Income Tax Increase",
            official_10yr=-252.0,
            official_source="U.S. Treasury",
            model_10yr=-250.0,
            model_first_year=-25.0,
            difference=2.0,
            percent_difference=-0.8,
            direction_match=True,
            accuracy_rating="Excellent",
            benchmark_kind="Published administration estimate",
            benchmark_date="2024-03",
        ),
        ValidationResult(
            policy_id="biden_ctc_2021",
            policy_name="Biden 2021 ARP-style CTC (permanent)",
            official_10yr=1600.0,
            official_source="Congressional Budget Office",
            model_10yr=1743.0,
            model_first_year=174.0,
            difference=143.0,
            percent_difference=8.9,
            direction_match=True,
            accuracy_rating="Good",
            notes="Permanent-policy extrapolation of an ARP-style benchmark.",
            benchmark_kind="Official budget score",
            benchmark_date="2021-03",
            benchmark_url="https://www.cbo.gov/",
            known_limitations=[
                "Credit eligibility and refundability are modeled with synthetic tax units rather than CPS ASEC microdata.",
            ],
        ),
    ]

    report = generate_validation_report(results)

    assert "## Benchmark Coverage" in report
    assert "## Manuscript Checkpoints" in report
    assert "## Current Evidence Boundaries" in report
    assert "Biden 2021 ARP-style CTC (permanent)" in report
    assert "synthetic tax units rather than CPS ASEC microdata" in report
    assert "Congressional Budget Office (2021-03)" in report


def test_generate_validation_report_handles_empty_results():
    report = generate_validation_report([])

    assert "No validation results were supplied." in report
    assert "## Current Evidence Boundaries" in report
