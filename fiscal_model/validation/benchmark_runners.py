"""
Concrete model runners for the CBO/JCT distributional benchmarks.

``cbo_distributions.run_full_cbo_jct_validation`` is parameterised by a
``model_runner`` callable so it can work with multiple engines. This
module supplies the canonical runner that uses the default
``DistributionalEngine`` from ``fiscal_model.distribution``. Each
benchmark maps to a policy factory + engine configuration; the runner
translates the benchmark's income grouping into the engine's
``IncomeGroupType`` and returns a result shaped for
``compare_distribution``.

Coverage today
--------------
- ``cbo_tcja_2018``       → TCJA full extension, deciles
- ``jct_tcja_2019``       → TCJA full extension, JCT dollar brackets
- ``cbo_arp_2021``        → Biden CTC 2021, quintiles (best available)
- ``jct_salt_repeal_2024`` → *not yet* — needs TaxExpenditurePolicy path
- ``jct_corporate_28_2022`` → Biden corporate 28%, JCT dollar brackets

The engine returns group labels (``"Middle Quintile"``, ``"$100k-$200k"``
etc.) that differ from the benchmark labels; a label-map normalises them
so ``compare_distribution`` finds overlap.
"""

from __future__ import annotations

import logging
from typing import Any

from fiscal_model.distribution import DistributionalEngine, IncomeGroupType
from fiscal_model.validation.cbo_distributions import (
    CBODistributionalBenchmark,
    IncomeGroupingType,
)

logger = logging.getLogger(__name__)


# Benchmark ID → (policy_factory, engine_group_type)
_BENCHMARK_POLICIES: dict[str, tuple[str, IncomeGroupType]] = {
    "cbo_tcja_2018": ("create_tcja_extension", IncomeGroupType.DECILE),
    "jct_tcja_2019": ("create_tcja_extension", IncomeGroupType.JCT_DOLLAR),
    "cbo_tcja_extension_2026": (
        "create_tcja_extension",
        IncomeGroupType.DECILE,
    ),
    "cbo_arp_2021": ("create_biden_ctc_2021", IncomeGroupType.QUINTILE),
    "jct_corporate_28_2022": (
        "create_biden_corporate_rate_only",
        IncomeGroupType.JCT_DOLLAR,
    ),
    "jct_salt_repeal_2024": (
        "create_repeal_salt_cap",
        IncomeGroupType.JCT_DOLLAR,
    ),
}


# Benchmark group label → engine group label. The engine uses titlecase
# with a trailing " Quintile" / " Decile" suffix and plain dollar
# brackets like "$100k-$200k" (no en-dash).
_LABEL_NORMALIZATION = {
    # Quintile labels
    "Lowest quintile": "Lowest Quintile",
    "Second quintile": "Second Quintile",
    "Middle quintile": "Middle Quintile",
    "Fourth quintile": "Fourth Quintile",
    "Highest quintile": "Top Quintile",
    # Decile labels — engine emits "1st Decile" .. "10th Decile"
    "Decile 1 (lowest)": "1st Decile",
    "Decile 2": "2nd Decile",
    "Decile 3": "3rd Decile",
    "Decile 4": "4th Decile",
    "Decile 5": "5th Decile",
    "Decile 6": "6th Decile",
    "Decile 7": "7th Decile",
    "Decile 8": "8th Decile",
    "Decile 9": "9th Decile",
    "Decile 10 (highest)": "10th Decile",
    # JCT dollar brackets — engine emits uppercase K, en-dashes become hyphens,
    # and the top bucket reads "$1M and over".
    "<$10k": "Less than $10K",
    "$10k–$20k": "$10K-$20K",
    "$20k–$30k": "$20K-$30K",
    "$30k–$40k": "$30K-$40K",
    "$30k–$50k": "$30K-$50K",
    "$40k–$50k": "$40K-$50K",
    "$50k–$75k": "$50K-$75K",
    "$50k–$100k": "$50K-$100K",
    "$75k–$100k": "$75K-$100K",
    "$100k–$200k": "$100K-$200K",
    "$200k–$500k": "$200K-$500K",
    "$500k–$1M": "$500K-$1M",
    "$1M+": "$1M and over",
    "<$30k": "Less than $10K",  # JCT corporate benchmark aggregates low end
    "<$50k": "Less than $10K",  # SALT benchmark aggregates further
}


def _policy_factory(benchmark_id: str) -> Any | None:
    """Return the constructed policy for a benchmark, or None if unmapped."""
    if benchmark_id not in _BENCHMARK_POLICIES:
        return None
    factory_name, _ = _BENCHMARK_POLICIES[benchmark_id]

    try:
        if factory_name == "create_tcja_extension":
            from fiscal_model.tcja import create_tcja_extension

            return create_tcja_extension(extend_all=True, keep_salt_cap=True)
        if factory_name == "create_biden_ctc_2021":
            from fiscal_model.credits import create_biden_ctc_2021

            return create_biden_ctc_2021()
        if factory_name == "create_biden_corporate_rate_only":
            from fiscal_model.corporate import create_biden_corporate_rate_only

            return create_biden_corporate_rate_only()
        if factory_name == "create_repeal_salt_cap":
            from fiscal_model.tax_expenditures import create_repeal_salt_cap

            return create_repeal_salt_cap()
    except Exception:
        logger.exception("Failed to construct policy for %s", benchmark_id)
        return None
    return None


def _normalize_labels(result: Any) -> Any:
    """Rewrite engine group labels to match benchmark labels where mapped."""
    for row in getattr(result, "results", []):
        name = getattr(getattr(row, "income_group", None), "name", None)
        if name is None:
            continue
        # Reverse lookup: if any benchmark label maps to this engine label,
        # relabel the row to the benchmark form so ``compare_distribution``
        # can match it.
        for bench_label, engine_label in _LABEL_NORMALIZATION.items():
            if engine_label == name:
                row.income_group.name = bench_label
                break
    return result


def default_model_runner(benchmark: CBODistributionalBenchmark) -> Any | None:
    """
    Run the DistributionalEngine against a benchmark's implied policy.

    Returns a result that ``compare_distribution`` can consume, or
    ``None`` when the benchmark is unmapped (the full validation runner
    skips ``None``s).
    """
    policy = _policy_factory(benchmark.policy_id)
    if policy is None:
        return None

    _, group_type = _BENCHMARK_POLICIES[benchmark.policy_id]
    # Map benchmark-published grouping when it differs from our engine's.
    if benchmark.grouping == IncomeGroupingType.DECILE:
        group_type = IncomeGroupType.DECILE
    elif benchmark.grouping == IncomeGroupingType.QUINTILE:
        group_type = IncomeGroupType.QUINTILE
    elif benchmark.grouping == IncomeGroupingType.AGI_CLASS:
        group_type = IncomeGroupType.JCT_DOLLAR

    engine = DistributionalEngine(data_year=benchmark.analysis_year)
    try:
        result = engine.analyze_policy(policy, group_type=group_type)
    except Exception:
        logger.exception("DistributionalEngine failed on %s", benchmark.policy_id)
        return None

    return _normalize_labels(result)


__all__ = ["default_model_runner"]
