"""
Reporting helpers for validation results.
"""

from collections import Counter

import numpy as np

from ..time_utils import utc_now
from .core import ValidationResult


_MANUSCRIPT_EVIDENCE_BOUNDARIES = [
    "Aggregate fiscal validation is stronger than distributional validation in the current repo.",
    "Distributional validation still leans mainly on published TPC tables rather than a broader CBO distributional benchmark set.",
    "Household and payroll modules still rely on synthetic tax units or aggregate wage distributions rather than CPS ASEC or SSA microdata.",
    "Current manuscript claims should present point errors alongside known limitations rather than treating the benchmark table as a full uncertainty interval.",
]


def _format_billions(value: float) -> str:
    """Format a billions value for markdown tables."""
    return f"${value:,.0f}B"


def _format_benchmark_label(result: ValidationResult) -> str:
    """Format a compact benchmark label for markdown tables."""
    if result.benchmark_date:
        return f"{result.official_source} ({result.benchmark_date})"
    return result.official_source


def _format_follow_up(result: ValidationResult) -> str:
    """Summarize whether a scenario needs explicit discussion."""
    if result.needs_follow_up:
        return "Yes"
    return "No"


def _results_needing_follow_up(results: list[ValidationResult]) -> list[ValidationResult]:
    """Return scenarios that should be called out in a manuscript appendix."""
    return sorted(
        [result for result in results if result.needs_follow_up],
        key=lambda result: result.abs_percent_difference,
        reverse=True,
    )


def generate_validation_report(results: list[ValidationResult]) -> str:
    """
    Generate a markdown validation report.
    """
    lines = [
        "# Model Validation Report",
        "",
        f"**Date:** {utc_now().strftime('%Y-%m-%d')}",
        f"**Policies Tested:** {len(results)}",
        "",
        "## Summary",
        "",
    ]

    if not results:
        lines.extend(
            [
                "- No validation results were supplied.",
                "",
                "## Current Evidence Boundaries",
                "",
            ]
        )
        lines.extend(f"- {note}" for note in _MANUSCRIPT_EVIDENCE_BOUNDARIES)
        return "\n".join(lines)

    accurate = sum(1 for result in results if result.is_accurate)
    direction_ok = sum(1 for result in results if result.direction_match)
    absolute_errors = [result.abs_percent_difference for result in results]
    follow_up = _results_needing_follow_up(results)

    lines.extend(
        [
            f"- **Accuracy Rate:** {accurate}/{len(results)} within 20% ({accurate/len(results)*100:.0f}%)",
            f"- **Direction Match:** {direction_ok}/{len(results)} ({direction_ok/len(results)*100:.0f}%)",
            f"- **Mean Error:** {np.mean(absolute_errors):.1f}%",
            f"- **Median Error:** {np.median(absolute_errors):.1f}%",
            f"- **Manuscript Checkpoints:** {len(follow_up)} scenario(s) need explicit caveats or follow-up",
            "",
            "## Benchmark Coverage",
            "",
            "| Source | Policies | Benchmark Kind |",
            "|--------|----------|----------------|",
        ]
    )

    for (source, benchmark_kind), count in sorted(
        Counter((result.official_source, result.benchmark_kind) for result in results).items()
    ):
        lines.append(f"| {source} | {count} | {benchmark_kind} |")

    lines.extend(
        [
            "",
            "## Detailed Results",
            "",
            "| Policy | Benchmark | Official | Model | Diff | % Error | Rating | Follow-up |",
            "|--------|-----------|----------|-------|------|---------|--------|-----------|",
        ]
    )

    for result in sorted(results, key=lambda item: item.abs_percent_difference):
        lines.append(
            f"| {result.policy_name[:36]} | "
            f"{_format_benchmark_label(result)} | "
            f"{_format_billions(result.official_10yr)} | "
            f"{_format_billions(result.model_10yr)} | "
            f"{_format_billions(result.difference)} | "
            f"{result.percent_difference:+.1f}% | "
            f"{result.accuracy_rating} | "
            f"{_format_follow_up(result)} |"
        )

    lines.extend(
        [
            "",
            "## Manuscript Checkpoints",
            "",
            "These are the scenarios that should be explained directly in a paper, appendix, or limitations section rather than left implicit.",
            "",
        ]
    )

    if follow_up:
        for result in follow_up:
            lines.extend(
                [
                    f"### {result.policy_name}",
                    "",
                    f"- **Benchmark:** {_format_benchmark_label(result)}",
                    f"- **Benchmark type:** {result.benchmark_kind}",
                    f"- **Point error:** {result.percent_difference:+.1f}% ({result.accuracy_rating})",
                ]
            )
            if result.notes:
                lines.append(f"- **Context:** {result.notes}")
            for limitation in result.known_limitations:
                lines.append(f"- **Limitation:** {limitation}")
            if result.benchmark_url:
                lines.append(f"- **Source URL:** {result.benchmark_url}")
            lines.append("")
    else:
        lines.extend(
            [
                "- No scenarios crossed the follow-up threshold in this result set.",
                "",
            ]
        )

    lines.extend(
        [
            "## Current Evidence Boundaries",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in _MANUSCRIPT_EVIDENCE_BOUNDARIES)

    lines.extend(
        [
            "",
            "## Interpretation Guide",
            "",
            "| Rating | % Error | Interpretation |",
            "|--------|---------|----------------|",
            "| Excellent | <=5% | Model closely matches the published benchmark |",
            "| Good | 5-10% | Model is reasonably accurate but still worth footnoting in a manuscript |",
            "| Acceptable | 10-20% | Directionally useful, but the appendix should explain model simplifications |",
            "| Poor | >20% | Significant deviation - investigate methodology before relying on the result |",
        ]
    )

    return "\n".join(lines)
