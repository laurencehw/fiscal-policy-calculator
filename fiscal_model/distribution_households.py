"""
CBO's household universe for distributional analysis.

Why this module exists
----------------------
The distributional engine ranks **tax units** by AGI into buckets cut at fixed
2024 dollar thresholds. CBO ranks **households** by size-adjusted income before
transfers and taxes into groups holding equal numbers of **people**. Those are
different universes, and the bottom of the distribution is where they differ
most: CPS tax-unit construction splits a household into filing, non-filing and
dependent units, so 33.8M weighted units sit at AGI <= 0 and 96.8M — 50.6% of
the universe, not 20% — fall below the engine's $35,000 "Lowest Quintile"
boundary. A refundable per-person credit scored on that universe books its
dollars in a bucket CBO does not have.

This module is the household layer. It does not replace the tax-unit path;
``DistributionalEngine`` chooses between them with ``unit="tax_unit"`` (the
default, and what the TPC/JCT return-level tables want) and ``unit="household"``
(what CBO's tables want).

CBO's methodology, which is what is implemented here
----------------------------------------------------
Four definitions, all published, none tuned to a benchmark. Sources: CBO, *The
Distribution of Household Income* (https://www.cbo.gov/publication/60706) and
the methodology working paper *Current Work on the Distributional Analysis of
Household Income* (https://www.cbo.gov/system/files/2022-12/58508-WP.pdf).

1. **The unit is the household** — the people sharing a housing unit, whatever
   their relationship to each other. The CPS household sequence number is that
   unit, and it survives into the derived microdata as ``household_id``.

2. **The ranking income is income before transfers and taxes**, which CBO
   defines as *"market income plus social insurance benefits"*. Market income is
   *"labor income, business income, capital gains (profits realized from the
   sale of assets), capital income excluding capital gains, income received in
   retirement for past services, and other nongovernmental sources of income"*;
   social insurance benefits are *"Social Security and Medicare benefits,
   regular unemployment insurance ... and workers' compensation"*.

3. **Income is adjusted for household size**: *"CBO calculates adjusted
   household income by dividing household income by the square root of the
   number of people in the household,"* and *"CBO adjusts income for household
   size only for the purpose of ranking households and assigning them to income
   groups. All other income measures in the agency's distributional analyses are
   unadjusted."* So the exponent is one half, it touches only the ranking key,
   and every reported dollar below is unadjusted.

4. **Groups hold equal numbers of people**: CBO ranks individuals by their
   household's adjusted income and cuts the ranking into groups *"each
   containing roughly an equal number of people"*; *"the quintiles contain equal
   numbers of people, but because households vary in size, quintiles generally
   contain unequal numbers of households."* Averages are then reported per
   household.

What the CPS extract cannot supply
----------------------------------
Three components of CBO's market income are not in the derived microdata and are
named here rather than proxied: business income, retirement income for past
services other than Social Security, and the imputed value of Medicare benefits.
Means-tested transfers are absent too, which is harmless — CBO's *ranking*
measure excludes them by construction.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .distribution_core import IncomeGroup, IncomeGroupType
from .distribution_grouping import get_group_thresholds

#: CBO divides household income by the square root of household size. The
#: exponent is one half exactly; it is a published equivalence scale, not a
#: parameter this repository is free to choose.
HOUSEHOLD_EQUIVALENCE_EXPONENT = 0.5

#: The universes ``DistributionalEngine`` understands.
TAX_UNIT = "tax_unit"
HOUSEHOLD = "household"
SUPPORTED_UNITS = (TAX_UNIT, HOUSEHOLD)

#: Group types the household ranking can express. Dollar-bracket groupings are
#: a *filing-unit* construct — JCT publishes them by AGI class of tax return —
#: so they stay on the tax-unit path rather than being reinterpreted.
HOUSEHOLD_GROUP_COUNTS = {
    IncomeGroupType.QUINTILE: 5,
    IncomeGroupType.DECILE: 10,
}

#: Columns the household layer reads off the tax-unit frame.
REQUIRED_COLUMNS = (
    "household_id",
    "household_weight",
    "household_persons",
    "agi",
    "social_security",
)


def supports_household_universe(microdata: pd.DataFrame) -> bool:
    """Whether ``microdata`` carries the household layer's inputs."""
    return set(REQUIRED_COLUMNS) <= set(microdata.columns)


def aggregate_to_households(
    microdata: pd.DataFrame,
    *,
    sum_columns: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Collapse a tax-unit frame to one row per household.

    ``household_weight`` and ``household_persons`` are constant within a
    household, so they are read with ``first``. Every dollar column is summed
    across the household's tax units, unweighted: the household weight is
    applied once, at the household, which is what makes a per-household average
    a per-household average.

    Returns a frame indexed by ``household_id`` with, in addition to the summed
    columns:

    ``household_weight``
        CPS ASEC household supplement weight.
    ``household_persons``
        The household's roster count.
    ``income_before_transfers_and_taxes``
        CBO's ranking measure: market income plus social insurance benefits.
    ``adjusted_income``
        The same divided by the square root of household size — the ranking key,
        and nothing else.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in microdata.columns]
    if missing:
        raise KeyError(
            "The household universe needs "
            f"{', '.join(missing)} on the microdata. Rebuild the tax-unit file "
            "with `python -m fiscal_model.microsim.data_builder --fetch`."
        )

    aggregations: dict[str, tuple[str, str]] = {
        "household_weight": ("household_weight", "first"),
        "household_persons": ("household_persons", "first"),
        "agi": ("agi", "sum"),
        "social_security": ("social_security", "sum"),
    }
    for column in sum_columns:
        if column in microdata.columns and column not in aggregations:
            aggregations[column] = (column, "sum")

    households = microdata.groupby("household_id", sort=True).agg(**aggregations)

    # CBO: income before transfers and taxes is market income plus social
    # insurance benefits. On these columns ``agi`` is wages + interest +
    # dividends + realised gains + regular unemployment insurance, so adding
    # Social Security completes the definition over what the CPS extract holds.
    income = households["agi"] + households["social_security"]
    size = households["household_persons"].clip(lower=1)
    return households.assign(
        income_before_transfers_and_taxes=income,
        # The ranking key, and nothing else: CBO adjusts for household size
        # "only for the purpose of ranking households and assigning them to
        # income groups."
        adjusted_income=income / np.power(size, HOUSEHOLD_EQUIVALENCE_EXPONENT),
        person_weight=(
            households["household_weight"] * households["household_persons"]
        ),
    )


def assign_people_weighted_groups(
    households: pd.DataFrame,
    group_type: IncomeGroupType,
) -> pd.Series:
    """Return each household's 0-based group index under CBO's ranking.

    Households are sorted by adjusted income before transfers and taxes and cut
    into ``n`` groups holding equal numbers of *people*. A household straddling a
    boundary falls whole into the lower group, so the groups hold roughly — not
    exactly — equal numbers of people, which is CBO's own word for it.
    """
    if group_type not in HOUSEHOLD_GROUP_COUNTS:
        raise ValueError(
            f"The household universe has no {group_type} grouping: dollar-bracket "
            "groupings are a filing-unit construct and stay on the tax-unit path."
        )
    n_groups = HOUSEHOLD_GROUP_COUNTS[group_type]

    # ``mergesort`` is stable, so ties (many households sit at exactly $0) keep
    # household order and the assignment is reproducible.
    order = households["adjusted_income"].values.argsort(kind="mergesort")
    person_weight = households["person_weight"].values[order]
    cumulative = np.cumsum(person_weight)
    total = cumulative[-1] if len(cumulative) else 0.0
    if total <= 0:
        return pd.Series(0, index=households.index, dtype=int)

    edges = np.array([total * k / n_groups for k in range(1, n_groups)])
    group_of_sorted = np.minimum(
        np.searchsorted(edges, cumulative, side="left"), n_groups - 1
    )
    assigned = np.empty(len(households), dtype=int)
    assigned[order] = group_of_sorted
    return pd.Series(assigned, index=households.index, dtype=int)


def household_group_labels(group_type: IncomeGroupType) -> list[str]:
    """The engine's own group names, so benchmark label maps keep working."""
    return [name for name, _, _ in get_group_thresholds(group_type)]


def build_household_groups(
    households: pd.DataFrame,
    group_index: pd.Series,
    group_type: IncomeGroupType,
    *,
    tax_column: str = "final_tax",
) -> list[IncomeGroup]:
    """Build :class:`IncomeGroup` rows for the household universe.

    ``floor`` and ``ceiling`` are the group's observed range of *adjusted*
    income — the ranking key — because that is the quantity the boundary is a
    boundary in. Every dollar total on the group is unadjusted, per CBO.
    """
    labels = household_group_labels(group_type)
    total_weight = float(households["household_weight"].sum())
    groups: list[IncomeGroup] = []

    for index, label in enumerate(labels):
        members = households[group_index == index]
        if members.empty:
            groups.append(
                IncomeGroup(name=label, floor=0.0, ceiling=None, num_returns=0)
            )
            continue
        weight = members["household_weight"]
        weight_sum = float(weight.sum())
        floor = float(members["adjusted_income"].min())
        ceiling = (
            float(members["adjusted_income"].max()) if index < len(labels) - 1 else None
        )
        baseline_tax = (
            float((members[tax_column] * weight).sum() / 1e9)
            if tax_column in members.columns
            else 0.0
        )
        groups.append(
            IncomeGroup(
                name=label,
                floor=floor,
                ceiling=ceiling,
                # "Returns" is the engine's word for the unit being counted; in
                # this universe the unit is the household.
                num_returns=int(round(weight_sum)),
                total_agi=float(
                    (members["income_before_transfers_and_taxes"] * weight).sum() / 1e9
                ),
                total_taxable_income=float((members["agi"] * weight).sum() / 1e9),
                baseline_tax=baseline_tax,
                population_share=weight_sum / total_weight if total_weight > 0 else 0.0,
            )
        )
    return groups


__all__ = [
    "HOUSEHOLD",
    "HOUSEHOLD_EQUIVALENCE_EXPONENT",
    "HOUSEHOLD_GROUP_COUNTS",
    "REQUIRED_COLUMNS",
    "SUPPORTED_UNITS",
    "TAX_UNIT",
    "aggregate_to_households",
    "assign_people_weighted_groups",
    "build_household_groups",
    "household_group_labels",
    "supports_household_universe",
]
