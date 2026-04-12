"""
Reporting helpers for validation results.
"""

import numpy as np

from ..time_utils import utc_now
from .core import ValidationResult


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

    if results:
        accurate = sum(1 for result in results if result.is_accurate)
        direction_ok = sum(1 for result in results if result.direction_match)
        mean_err = np.mean([abs(result.percent_difference) for result in results])

        lines.extend(
            [
                f"- **Accuracy Rate:** {accurate}/{len(results)} within 20% ({accurate/len(results)*100:.0f}%)",
                f"- **Direction Match:** {direction_ok}/{len(results)} ({direction_ok/len(results)*100:.0f}%)",
                f"- **Mean Error:** {mean_err:.1f}%",
                "",
            ]
        )

    lines.extend(
        [
            "## Detailed Results",
            "",
            "| Policy | Official | Model | Diff | % Error | Rating |",
            "|--------|----------|-------|------|---------|--------|",
        ]
    )

    for result in results:
        lines.append(
            f"| {result.policy_name[:30]} | "
            f"${result.official_10yr:,.0f}B | "
            f"${result.model_10yr:,.0f}B | "
            f"${result.difference:+,.0f}B | "
            f"{result.percent_difference:+.1f}% | "
            f"{result.accuracy_rating} |"
        )

    lines.extend(
        [
            "",
            "## Methodology Notes",
            "",
            "- Model uses IRS SOI data for taxpayer counts and income distributions",
            "- Behavioral responses modeled via Elasticity of Taxable Income (ETI = 0.25)",
            "- Official scores may use different baselines and assumptions",
            "- Some variation expected due to data vintage differences",
            "",
            "## Interpretation Guide",
            "",
            "| Rating | % Error | Interpretation |",
            "|--------|---------|----------------|",
            "| Excellent | <=5% | Model closely matches official estimates |",
            "| Good | 5-10% | Model is reasonably accurate |",
            "| Acceptable | 10-20% | Model provides directional guidance |",
            "| Poor | >20% | Significant deviation - investigate methodology |",
        ]
    )

    return "\n".join(lines)
