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
- ``cbo_pl119_21_2026``    → P.L. 119-21 provision bundle, deciles
  (CBO's taxes-and-cash-transfers column only — see ``cbo_distributions``)

The engine returns group labels (``"Middle Quintile"``, ``"$100k-$200k"``
etc.) that differ from the benchmark labels; a label-map normalises them
so ``compare_distribution`` finds overlap.

Universes
---------
Each benchmark declares the universe *its own source* ranks
(``CBODistributionalBenchmark.ranking_universe``, with the source sentence in
``ranking_universe_source``), and the runner asks the engine for that universe.
CBO's four tables are households ranked by size-adjusted income before transfers
and taxes into people-weighted groups; JCT's three are income classes of tax
filing units. Comparing across the two is comparing different populations, which
is most of what the ARP benchmark's error was measuring before Wave 4.

The household universe needs the return-level microsim. Only the ARP bundle and
the SALT-cap repeal reach it today — every ``TCJAExtensionPolicy`` and the
corporate policy return an empty reform dict and take the synthetic bracket
path, which aggregates IRS return counts and has no household layer. For those,
the request degrades to the tax-unit path and the returned analysis says so on
``DistributionalAnalysis.unit``; the declaration is still worth carrying,
because it is a fact about the document and it is what a microsim path for those
policies would have to honour.

**Requested is not scored.** ``benchmark.ranking_universe`` is what the source
ranks and what this runner *asks* the engine for; the universe the model was
*scored* on is whatever comes back on ``DistributionalAnalysis.unit``, which
``compare_distribution`` records as ``BenchmarkComparison.scored_universe``.
Three of the four CBO tables — ``cbo_tcja_2018``, ``cbo_tcja_extension_2026``
and ``cbo_pl119_21_2026`` — are registered on ``household`` and scored on
``tax_unit`` for exactly the reason above, and every reporting surface (the
``/benchmarks`` and ``/summary`` API responses, ``run_validation_dashboard.py``
and the Methodology tab) shows both fields with the fallback marked. Every
runner returning a result for this suite must therefore set ``unit``: the
composite ARP merge propagates its components'.
"""

from __future__ import annotations

import logging
from typing import Any

from fiscal_model.distribution import (
    TAX_UNIT,
    DistributionalEngine,
    IncomeGroupType,
)
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
    # Phase D. CBO 61367's "federal taxes and cash transfers" column for
    # P.L. 119-21 is dominated by the eight provisions scored line by line in
    # ``specialized_pl119_21.py`` - the TCJA rate schedule, standard deduction,
    # personal-exemption repeal, CTC, 199A, estate exemption, AMT and the SALT
    # cap - which together are exactly ``create_tcja_extension(extend_all=True,
    # keep_salt_cap=True)``. The mapping is that policy, not a new construction.
    "cbo_pl119_21_2026": ("create_tcja_extension", IncomeGroupType.DECILE),
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


def _combine_distributional_results(results: list[Any]) -> Any:
    """
    Combine multiple DistributionalAnalysis results into a composite.

    For each group, sum the per-policy *dollar effects* (share × total
    magnitude), then renormalize to shares of the combined total. This
    is the correct weighted merge — naive share-summing would
    double-count because each component's shares already sum to 1.0.

    Used to approximate composite policies (the ARP bundle = CTC +
    EITC childless + Recovery Rebate) for benchmarks that aggregate multiple
    provisions the engine scores separately.

    The merged result carries ``unit`` — the universe the components were
    actually ranked on — so ``compare_distribution`` can record what was
    scored rather than what was asked for. Components are scored by one engine
    on one universe, so the value is unanimous in practice; a disagreement
    would mean the merge spanned two populations, and the merged table is then
    reported on the weaker claim, ``tax_unit``. ``None`` means no component
    reported a universe.

    The per-group *average* is the **sum** of the components' averages, not
    their mean. Every component is scored over the same population and the
    same groups, so a household that gets $1,400 of rebate and $3,000 of child
    credit got $4,400; averaging the three components instead reported a third
    of the bundle, which is why the ARP row's dollar column read −$892 against
    CBO's −$2,800 while its *shares* — computed from the dollar-weighted merge
    below, and the only quantity ``compare_distribution`` scores — were right.
    """
    from types import SimpleNamespace

    if not results:
        return None

    # Each engine result has .total_tax_change in billions; use |total|
    # as the weight so components with larger magnitude contribute
    # proportionally more to the combined distribution.
    totals_by_group: dict[str, dict] = {}
    for res in results:
        component_total = float(getattr(res, "total_tax_change", 0.0))
        if component_total == 0:
            continue
        for row in res.results:
            name = row.income_group.name
            # Dollar effect on this group from this component (sign-preserving).
            dollar_effect = float(row.share_of_total_change) * abs(component_total)
            entry = totals_by_group.setdefault(
                name,
                {
                    "income_group": row.income_group,
                    "tax_change_avg_sum": 0.0,
                    "dollar_effect": 0.0,
                },
            )
            entry["tax_change_avg_sum"] += float(row.tax_change_avg)
            entry["dollar_effect"] += dollar_effect

    total_dollar_effect = sum(e["dollar_effect"] for e in totals_by_group.values())
    if total_dollar_effect == 0:
        return None

    units = {u for u in (getattr(res, "unit", None) for res in results) if u}
    if not units:
        merged_unit = None
    elif len(units) == 1:
        merged_unit = next(iter(units))
    else:
        logger.warning(
            "Composite merge spans more than one universe (%s); reporting the "
            "merged table on tax units.",
            ", ".join(sorted(units)),
        )
        merged_unit = TAX_UNIT

    combined_rows = []
    for entry in totals_by_group.values():
        normalized_share = entry["dollar_effect"] / total_dollar_effect
        avg_dollars = entry["tax_change_avg_sum"]
        combined_rows.append(
            SimpleNamespace(
                income_group=entry["income_group"],
                tax_change_avg=avg_dollars,
                share_of_total_change=normalized_share,
            )
        )
    return SimpleNamespace(results=combined_rows, unit=merged_unit)


def _run_arp_bundle(benchmark: CBODistributionalBenchmark) -> Any | None:
    """
    Score CBO's ARP 2021 bundle by composing the three provisions the
    official distributional analysis covers: expanded CTC, expanded
    childless EITC, and the Recovery Rebate. Each component is scored
    separately, then merged by dollar-weighted share
    (``_combine_distributional_results``).
    """
    from fiscal_model.credits import (
        create_arp_recovery_rebate,
        create_biden_ctc_2021,
        create_biden_eitc_childless,
    )

    engine = DistributionalEngine(
        data_year=benchmark.analysis_year, unit=benchmark.ranking_universe
    )
    components = [
        create_biden_ctc_2021(),
        create_biden_eitc_childless(),
        create_arp_recovery_rebate(),
    ]
    results = []
    for component in components:
        try:
            results.append(
                engine.analyze_policy(component, group_type=IncomeGroupType.QUINTILE)
            )
        except Exception:
            logger.exception("ARP component scoring failed: %s", component.name)
    return _combine_distributional_results(results)


def default_model_runner(
    benchmark: CBODistributionalBenchmark, *, prefer_microsim: bool = True
) -> Any | None:
    """
    Run the DistributionalEngine against a benchmark's implied policy.

    Returns a result that ``compare_distribution`` can consume, or
    ``None`` when the benchmark is unmapped (the full validation runner
    skips ``None``s).

    ``prefer_microsim`` (default True) selects the return-level microsim path
    where the policy supports it; pass False to force the synthetic
    bracket-aggregate reference path (used to check the calibrated tables).
    """
    # ARP is the one composite benchmark in the current suite: CBO's
    # published distribution covers three provisions the engine scores
    # separately. Route it through a bundle helper so the comparison
    # uses the right combined distribution.
    if benchmark.policy_id == "cbo_arp_2021":
        bundle = _run_arp_bundle(benchmark)
        return _normalize_labels(bundle) if bundle is not None else None

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

    engine = DistributionalEngine(
        data_year=benchmark.analysis_year, unit=benchmark.ranking_universe
    )
    try:
        result = engine.analyze_policy(
            policy, group_type=group_type, prefer_microsim=prefer_microsim
        )
    except Exception:
        logger.exception("DistributionalEngine failed on %s", benchmark.policy_id)
        return None

    return _normalize_labels(result)


__all__ = ["default_model_runner"]
