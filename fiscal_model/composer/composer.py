"""
Deterministic core of Package Studio — GoalSpec in, scored policy mixes out.

Nothing here is new estimation. Revenue components are drawn from the
app's validated preset library and built through the same
``preset_handler.create_policy_from_preset`` routing the Calculator and
the API use; every component is scored by the existing
:class:`~fiscal_model.scoring.FiscalPolicyScorer` and ranked by the
existing :class:`~fiscal_model.distribution.DistributionalEngine`. The
composer's own contribution is selection and sizing.

    GoalSpec
      ├─ spending goals ──▶ generic SpendingPolicy per goal (uncalibrated)
      ├─ deficit stance ──▶ 10-year revenue target
      └─ revenue philosophy ──▶ ordering over the preset revenue library
                                 └─▶ greedy selection up to the target
                                       └─▶ ScoredMix (path, totals, quintiles)

Sign convention is the engine's throughout: **positive adds to the
deficit**, so revenue raisers are negative and spending is positive.

Cost: scoring the whole revenue library and running its distributional
rankings takes a couple of seconds on a cold process. Both passes are
memoized at module level because Streamlit reruns the whole script on
every widget interaction — call :func:`reset_caches` in tests that need
a clean slate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from fiscal_model.app_data import PRESET_POLICIES
from fiscal_model.distribution import DistributionalEngine, IncomeGroupType
from fiscal_model.models.base import (
    DEFAULT_SCORER_START_YEAR,
    build_scorer_for_start_year,
    policy_start_year,
)
from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.policies_factory import create_spending_increase
from fiscal_model.policy_status import get_policy_status
from fiscal_model.preset_handler import create_policy_from_preset
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.ui.preset_validation import PRESET_TO_SCORECARD_ID, get_validation_badge

from .contracts import MixComponent, PolicyMix, ScoredMix
from .goal_spec import GoalSpec, SpendingGoal
from .progressivity import (
    PROPORTIONAL_TOP_QUINTILE_SHARE,
    PresetIncidence,
    measure_incidence,
    weighted_top_quintile_share,
)

logger = logging.getLogger(__name__)

# ── Sizing and selection parameters ─────────────────────────────────────
WINDOW_YEARS = 10
# Spending goals that arrive without a number are sized at a round
# placeholder rather than guessed from the label.
DEFAULT_ANNUAL_SPENDING_BILLIONS = 50.0
# "reduce" must beat spending by at least this much, per the stance's
# definition ("raise more than is spent").
MIN_DEFICIT_REDUCTION_BILLIONS = 1_500.0
# "invest" deliberately leaves half the spending unfunded.
INVEST_COVERAGE_SHARE = 0.5
# Packages stay readable: at most this many revenue lines.
MAX_REVENUE_COMPONENTS = 5
# A mix counts as hitting its target inside this band ...
COVERAGE_TOLERANCE = 0.15
# ... and may overshoot the remaining need by this much before the
# selector calls the component too big ("do not wildly oversize").
OVERSHOOT_ALLOWANCE = 0.30

_CUSTOM_PRESET = "Custom Policy"


# ── Candidates ──────────────────────────────────────────────────────────
@dataclass(frozen=True)
class RevenueCandidate:
    """One scored, ranked revenue preset available to the composer."""

    preset_name: str
    policy: Any
    start_year: int
    deficit_path: tuple[float, ...]     # deficit convention, 10 years
    ten_year_billions: float            # negative for a raiser
    incidence: PresetIncidence
    tier: str                           # "calibrated" | "generic"

    @property
    def magnitude(self) -> float:
        """Revenue raised over 10 years, as a positive number."""
        return abs(self.ten_year_billions)

    @property
    def top_quintile_share(self) -> float:
        return self.incidence.top_quintile_share


# Module-level caches. Streamlit reruns the script on every interaction,
# so rebuilding the library each time would re-score ~50 presets and
# re-run ~35 distributional analyses per keystroke.
_CANDIDATE_CACHE: list[RevenueCandidate] | None = None
_PRESET_SCORER_CACHE: dict[int, Any] = {}      # complex presets: use_real_data=False
_GENERIC_SCORER_CACHE: dict[int, Any] = {}     # simple rate/threshold presets


def reset_caches() -> None:
    """Drop the memoized candidate library and scorers. Mainly for tests."""
    global _CANDIDATE_CACHE
    _CANDIDATE_CACHE = None
    _PRESET_SCORER_CACHE.clear()
    _GENERIC_SCORER_CACHE.clear()


def _build_preset_policy(preset_name: str, preset_data: dict[str, Any]) -> tuple[Any, bool]:
    """Build a preset's policy object on the app's own routing path.

    Complex presets go through ``create_policy_from_preset`` — the single
    place where the calibrated TCJA / corporate / estate / payroll / …
    constructors live. The simple rate-and-threshold presets it returns
    ``None`` for are built as a plain ``TaxPolicy``, matching
    ``api._build_preset_policy`` and the comparison tabs.

    Returns ``(policy, use_real_data)`` — the generic path scores against
    live IRS SOI data, the calibrated constructors do not.
    """
    policy = create_policy_from_preset(preset_data)
    if policy is not None:
        return policy, False

    raw_rate_change = float(preset_data.get("rate_change", 0.0))
    policy = TaxPolicy(
        name=preset_name,
        description=preset_data.get("description", ""),
        policy_type=PolicyType.INCOME_TAX,
        rate_change=raw_rate_change / 100.0 if abs(raw_rate_change) > 1 else raw_rate_change,
        affected_income_threshold=float(preset_data.get("threshold", 0.0)),
        taxable_income_elasticity=0.25,
        duration_years=WINDOW_YEARS,
        ordinary_income_base=not bool(preset_data.get("agi_inclusive_base", False)),
    )
    return policy, True


def _scorer_for(policy: Any, use_real_data: bool) -> Any:
    """Scorer whose budget window starts with the policy, per model base."""
    cache = _GENERIC_SCORER_CACHE if use_real_data else _PRESET_SCORER_CACHE
    return build_scorer_for_start_year(
        FiscalPolicyScorer,
        start_year=policy_start_year(policy),
        use_real_data=use_real_data,
        cache=cache,
    )


def _tier_for(preset_name: str) -> str:
    """"calibrated" when a validation scorecard entry backs the preset."""
    return "calibrated" if preset_name in PRESET_TO_SCORECARD_ID else "generic"


def revenue_candidates() -> list[RevenueCandidate]:
    """Every preset that raises revenue, scored and ranked (memoized).

    "Raises revenue" means a negative 10-year ``final_deficit_effect`` —
    which includes the handful of presets that reduce the deficit through
    outlays (drug pricing) rather than through a tax. ``Custom Policy`` is
    not a scorable preset and is excluded.
    """
    global _CANDIDATE_CACHE
    if _CANDIDATE_CACHE is not None:
        return _CANDIDATE_CACHE

    engine = DistributionalEngine()
    candidates: list[RevenueCandidate] = []

    for preset_name, preset_data in PRESET_POLICIES.items():
        if preset_name == _CUSTOM_PRESET:
            continue
        try:
            policy, use_real_data = _build_preset_policy(preset_name, preset_data)
            result = _scorer_for(policy, use_real_data).score_policy(policy, dynamic=False)
        except Exception as exc:
            logger.warning("Composer skipping preset '%s': %s", preset_name, exc)
            continue

        path = tuple(float(value) for value in result.final_deficit_effect)
        ten_year = sum(path)
        if ten_year >= 0:
            continue  # a cost, not a raiser

        candidates.append(
            RevenueCandidate(
                preset_name=preset_name,
                policy=policy,
                start_year=policy_start_year(policy),
                deficit_path=path,
                ten_year_billions=ten_year,
                incidence=measure_incidence(
                    preset_name,
                    preset_data,
                    policy,
                    engine,
                    IncomeGroupType.QUINTILE,
                ),
                tier=_tier_for(preset_name),
            )
        )

    _CANDIDATE_CACHE = candidates
    return candidates


# ── Selection strategies ────────────────────────────────────────────────
def _order_top_heavy(candidates: list[RevenueCandidate]) -> list[RevenueCandidate]:
    """Most burden-concentrated raisers first."""
    return sorted(
        candidates,
        key=lambda c: (-c.top_quintile_share, -c.magnitude, c.preset_name),
    )


def _order_broad(candidates: list[RevenueCandidate]) -> list[RevenueCandidate]:
    """Closest-to-proportional raisers first.

    Distance from the top quintile's own share of the tax base, so this
    passes over both the ultra-concentrated raisers and the ones whose
    burden falls furthest below the top. Raisers that are not household
    taxes at all (outlay-side savings) go last: their placeholder share
    would otherwise read as "conveniently proportional".
    """
    return sorted(
        candidates,
        key=lambda c: (
            0 if c.incidence.is_household_tax else 1,
            abs(c.top_quintile_share - PROPORTIONAL_TOP_QUINTILE_SHARE),
            -c.magnitude,
            c.preset_name,
        ),
    )


def _order_corporate_first(candidates: list[RevenueCandidate]) -> list[RevenueCandidate]:
    """Corporate-side raisers first, then the top-heavy ordering."""
    return sorted(
        candidates,
        key=lambda c: (
            0 if c.incidence.is_corporate else 1,
            -c.magnitude if c.incidence.is_corporate else -c.top_quintile_share,
            c.preset_name,
        ),
    )


def _order_balanced(candidates: list[RevenueCandidate]) -> list[RevenueCandidate]:
    """Alternate the top-heavy and broad orderings."""
    top_heavy = _order_top_heavy(candidates)
    broad = _order_broad(candidates)
    ordered: list[RevenueCandidate] = []
    seen: set[str] = set()
    for pair in zip(top_heavy, broad):
        for candidate in pair:
            if candidate.preset_name not in seen:
                seen.add(candidate.preset_name)
                ordered.append(candidate)
    return ordered


@dataclass(frozen=True)
class _Strategy:
    key: str
    name: str
    rationale: str
    order: Any  # Callable[[list[RevenueCandidate]], list[RevenueCandidate]]


_STRATEGIES: dict[str, _Strategy] = {
    "top_heavy": _Strategy(
        "top_heavy",
        "Top-heavy",
        "Leads with the raisers whose burden lands most heavily on the top "
        "quintile, so the package is funded from the highest incomes",
        _order_top_heavy,
    ),
    "broad": _Strategy(
        "broad",
        "Broader base",
        "Favours raisers whose incidence sits near the top quintile's own "
        "share of the tax base, spreading the burden closer to proportional",
        _order_broad,
    ),
    "corporate": _Strategy(
        "corporate",
        "With corporate",
        "Reaches for corporate-side raisers — the rate, the book minimum "
        "tax and the international regime — before individual taxes",
        _order_corporate_first,
    ),
    "balanced": _Strategy(
        "balanced",
        "Balanced mix",
        "Alternates top-heavy and broad-base raisers so neither side of the "
        "package carries the whole target",
        _order_balanced,
    ),
}

# Preference order per philosophy: the first entry is the philosophy's own
# reading of the spec, the rest are the contrasting variants offered
# alongside it.
_PHILOSOPHY_STRATEGIES: dict[str, tuple[str, ...]] = {
    "progressive": ("top_heavy", "broad", "corporate", "balanced"),
    "broad_base": ("broad", "top_heavy", "corporate", "balanced"),
    "corporate": ("corporate", "top_heavy", "broad", "balanced"),
    "mixed": ("balanced", "top_heavy", "broad", "corporate"),
}


def _select_revenue(
    ordered: list[RevenueCandidate],
    target_billions: float,
) -> list[RevenueCandidate]:
    """Pick components in preference order until the target is covered.

    The philosophy's ordering leads: the walk never reaches past a
    candidate it can afford. Because each ordering breaks ties by size,
    the largest acceptable raiser in the preferred band comes first, which
    is what "prefer fewer, larger components over many slivers" buys —
    the walk then refuses anything that would overshoot what is *still*
    needed by more than :data:`OVERSHOOT_ALLOWANCE`. A final closing pick
    fills a gap the greedy pass could not.
    """
    if target_billions <= 0 or not ordered:
        return []

    lower = target_billions * (1 - COVERAGE_TOLERANCE)

    chosen: list[RevenueCandidate] = []
    chosen_names: set[str] = set()
    total = 0.0
    for candidate in ordered:
        if len(chosen) >= MAX_REVENUE_COMPONENTS or total >= lower:
            break
        remaining = target_billions - total
        if candidate.magnitude <= remaining * (1 + OVERSHOOT_ALLOWANCE):
            chosen.append(candidate)
            chosen_names.add(candidate.preset_name)
            total += candidate.magnitude

    if total < lower and len(chosen) < MAX_REVENUE_COMPONENTS:
        gap = target_billions - total
        unused = [c for c in ordered if c.preset_name not in chosen_names]
        covering = [c for c in unused if c.magnitude >= gap]
        closer = (
            min(covering, key=lambda c: (c.magnitude, c.preset_name))
            if covering
            else max(unused, key=lambda c: (c.magnitude, c.preset_name), default=None)
        )
        if closer is not None:
            chosen.append(closer)

    return chosen


# ── Spending ────────────────────────────────────────────────────────────
# GoalSpec categories → the three budget categories SpendingPolicy models.
# The class derives its PolicyType from this category, so the mapping is
# the only lever that matters.
_CATEGORY_TO_BUDGET_CATEGORY: dict[str, str] = {
    "infrastructure": "nondefense",
    "education": "nondefense",
    "research": "nondefense",
    "climate": "nondefense",
    "other": "nondefense",
    "defense": "defense",
    "healthcare": "mandatory",
    "safety_net": "mandatory",
}


def _build_spending_policy(goal: SpendingGoal, start_year: int) -> Any:
    """One generic, uncalibrated SpendingPolicy for a spending goal."""
    annual = goal.annual_billions
    if annual is None or annual <= 0:
        annual = DEFAULT_ANNUAL_SPENDING_BILLIONS
    policy = create_spending_increase(
        name=goal.label,
        annual_billions=float(annual),
        category=_CATEGORY_TO_BUDGET_CATEGORY.get(goal.category, "nondefense"),
        start_year=start_year,
        duration=WINDOW_YEARS,
    )
    policy.description = f"{goal.label}: ${annual:,.0f}B/yr of {goal.category} spending"
    return policy


def _score_spending_goals(
    spec: GoalSpec,
) -> tuple[list[MixComponent], list[tuple[float, ...]]]:
    """Score every spending goal once; the same components go in every mix.

    Returns the components and their deficit paths, in
    ``spec.spending_goals`` order.
    """
    components: list[MixComponent] = []
    paths: list[tuple[float, ...]] = []
    for goal in spec.spending_goals:
        policy = _build_spending_policy(goal, DEFAULT_SCORER_START_YEAR)
        result = _scorer_for(policy, use_real_data=False).score_policy(policy, dynamic=False)
        path = tuple(float(value) for value in result.final_deficit_effect)
        ten_year = sum(path)
        paths.append(path)
        components.append(
            MixComponent(
                label=goal.label,
                kind="spending",
                preset_name=None,
                ten_year_billions=ten_year,
                annual_billions=ten_year / WINDOW_YEARS,
                validation_badge=None,
                policy_status=None,
                tier="spending",
            )
        )
    return components, paths


def revenue_target_billions(spec: GoalSpec, spending_10yr_billions: float) -> float:
    """10-year revenue the mix should raise, as a positive number.

    ``neutral`` covers the spending, ``reduce`` covers it and then some,
    ``invest`` covers roughly half. A user's explicit floor
    (``min_revenue_10yr_billions``) applies on top of any stance.
    """
    spending = max(0.0, spending_10yr_billions)
    if spec.deficit_stance == "reduce":
        floor = spec.min_revenue_10yr_billions or MIN_DEFICIT_REDUCTION_BILLIONS
        target = spending + max(floor, MIN_DEFICIT_REDUCTION_BILLIONS)
    elif spec.deficit_stance == "invest":
        target = spending * INVEST_COVERAGE_SHARE
    else:  # neutral
        target = spending
    return max(target, spec.min_revenue_10yr_billions or 0.0)


# ── Assembly ────────────────────────────────────────────────────────────
def _revenue_component(candidate: RevenueCandidate) -> MixComponent:
    return MixComponent(
        label=candidate.preset_name,
        kind="revenue",
        preset_name=candidate.preset_name,
        ten_year_billions=candidate.ten_year_billions,
        annual_billions=candidate.ten_year_billions / WINDOW_YEARS,
        validation_badge=get_validation_badge(candidate.preset_name),
        policy_status=get_policy_status(candidate.preset_name),
        tier=candidate.tier,
    )


def _distribution_rows(
    chosen: list[RevenueCandidate],
) -> tuple[tuple[dict[str, Any], ...], list[str]]:
    """Quintile rows summed over the representable revenue components.

    Returns the rows plus the names of components the distributional
    engine could not represent, which the caller turns into a caveat.
    """
    totals: dict[str, float] = {}
    order: list[str] = []
    unrepresented: list[str] = []

    for candidate in chosen:
        if not candidate.incidence.representable:
            unrepresented.append(candidate.preset_name)
            continue
        for group, value in candidate.incidence.quintile_billions:
            if group not in totals:
                totals[group] = 0.0
                order.append(group)
            totals[group] += value

    grand_total = sum(totals.values())
    rows = tuple(
        {
            "group": group,
            "tax_change_billions": totals[group],
            "share_of_total": (totals[group] / grand_total) if grand_total > 0 else 0.0,
        }
        for group in order
    )
    return rows, unrepresented


def top_quintile_burden_share(components: list[MixComponent]) -> float:
    """Revenue-weighted share of a mix's burden landing in the top quintile.

    Uses the engine's quintile split where a component is representable
    and the documented fallback in ``progressivity.py`` where it is not,
    so every revenue component is counted. Ranking summary, not a scored
    distributional result.
    """
    by_name = {c.preset_name: c for c in revenue_candidates()}
    weighted = [
        (abs(component.ten_year_billions), by_name[component.preset_name].top_quintile_share)
        for component in components
        if component.kind == "revenue" and component.preset_name in by_name
    ]
    return weighted_top_quintile_share(weighted)


def _build_caveats(
    chosen: list[RevenueCandidate],
    spending_components: list[MixComponent],
    unrepresented: list[str],
    revenue_10yr: float,
    target_billions: float,
) -> tuple[str, ...]:
    """Honesty strings rendered under every mix."""
    caveats: list[str] = [
        "Components are scored independently and then summed: interactions "
        "between them — overlapping bases, stacked marginal rates, "
        "behavioral spillovers — are not modeled, so the package total is "
        "not a joint estimate.",
        "The revenue distribution covers the revenue side only. Spending "
        "incidence is not modeled, so the quintile table says nothing about "
        "who benefits from the spending in this package.",
    ]

    if unrepresented:
        caveats.append(
            "The distributional engine returns no household rows for "
            + ", ".join(unrepresented)
            + ", so those components are excluded from the quintile table "
            "(they are still in the budget total)."
        )

    outlay_side = [
        c.preset_name for c in chosen if c.incidence.family == "outlay_side"
    ]
    if outlay_side:
        caveats.append(
            "Some components reduce the deficit through outlays rather than "
            "taxes (" + ", ".join(outlay_side) + "), so they have no "
            "household tax burden to distribute."
        )

    if spending_components:
        caveats.append(
            "Spending components are generic SpendingPolicy builds sized "
            "from the goal, not calibrated program scores — treat their "
            "totals as the cost of the stated dollar amount, not as an "
            "estimate of what the program would cost."
        )

    start_years = sorted({c.start_year for c in chosen})
    if len(start_years) > 1:
        caveats.append(
            "Components take effect in different years ("
            + ", ".join(str(year) for year in start_years)
            + "); each is scored over its own 10-year window and the paths "
            "are summed by year of effect."
        )

    if target_billions > 0:
        raised = abs(revenue_10yr)
        if raised < target_billions * (1 - COVERAGE_TOLERANCE):
            caveats.append(
                f"This mix raises ${raised:,.0f}B against a "
                f"${target_billions:,.0f}B target — the preset library has "
                "no combination that closes the gap."
            )
        elif raised > target_billions * (1 + OVERSHOOT_ALLOWANCE):
            caveats.append(
                f"This mix raises ${raised:,.0f}B against a "
                f"${target_billions:,.0f}B target; the smallest available "
                "raiser that covers the target overshoots it."
            )

    return tuple(caveats)


def _score_mix(
    name: str,
    rationale: str,
    chosen: list[RevenueCandidate],
    spending_components: list[MixComponent],
    spending_paths: list[tuple[float, ...]],
    target_billions: float,
) -> ScoredMix:
    """Assemble and total one variant."""
    components = [_revenue_component(c) for c in chosen] + list(spending_components)
    mix = PolicyMix(name=name, rationale=rationale, components=tuple(components))

    paths = [c.deficit_path for c in chosen] + spending_paths
    combined = [0.0] * WINDOW_YEARS
    for path in paths:
        for index, value in enumerate(path[:WINDOW_YEARS]):
            combined[index] += value

    window_start = min(
        [c.start_year for c in chosen] + [DEFAULT_SCORER_START_YEAR],
    )
    years = tuple(range(window_start, window_start + WINDOW_YEARS))

    revenue_10yr = sum(c.ten_year_billions for c in chosen)
    spending_10yr = sum(c.ten_year_billions for c in spending_components)
    rows, unrepresented = _distribution_rows(chosen)

    return ScoredMix(
        mix=mix,
        years=years,
        deficit_path_billions=tuple(combined),
        ten_year_deficit_billions=sum(combined),
        revenue_10yr_billions=revenue_10yr,
        spending_10yr_billions=spending_10yr,
        revenue_distribution_rows=rows,
        caveats=_build_caveats(
            chosen,
            spending_components,
            unrepresented,
            revenue_10yr,
            target_billions,
        ),
    )


def compose_and_score(spec: GoalSpec, *, n_mixes: int = 3) -> list[ScoredMix]:
    """Turn a GoalSpec into scored policy mixes, best reading of the spec first.

    Deterministic: the same spec always yields the same mixes, because
    selection is an ordering over a fixed, fully scored preset library
    with explicit tie-breaks.

    Raises:
        ValueError: if ``spec.validate()`` reports problems.
    """
    problems = spec.validate()
    if problems:
        raise ValueError("Invalid GoalSpec: " + "; ".join(problems))
    if n_mixes < 1:
        return []

    spending_components = _score_spending_goals(spec)
    spending_paths = _spending_paths(spec)
    spending_10yr = sum(c.ten_year_billions for c in spending_components)
    target = revenue_target_billions(spec, spending_10yr)

    candidates = revenue_candidates()
    strategy_keys = _PHILOSOPHY_STRATEGIES.get(
        spec.revenue_philosophy,
        _PHILOSOPHY_STRATEGIES["mixed"],
    )

    mixes: list[ScoredMix] = []
    seen_selections: list[frozenset[str]] = []
    for key in strategy_keys:
        if len(mixes) >= n_mixes:
            break
        strategy = _STRATEGIES[key]
        chosen = _select_revenue(strategy.order(candidates), target)
        selection = frozenset(c.preset_name for c in chosen)
        # Variants must read differently; a strategy that lands on an
        # already-used selection is skipped in favour of the next one.
        if mixes and selection in seen_selections:
            continue
        seen_selections.append(selection)
        rationale = (
            f"{strategy.rationale}; sized to raise about ${target:,.0f}B over "
            f"10 years for a '{spec.deficit_stance}' stance."
        )
        mixes.append(
            _score_mix(
                strategy.name,
                rationale,
                chosen,
                spending_components,
                spending_paths,
                target,
            )
        )

    return mixes


__all__ = [
    "COVERAGE_TOLERANCE",
    "DEFAULT_ANNUAL_SPENDING_BILLIONS",
    "MAX_REVENUE_COMPONENTS",
    "MIN_DEFICIT_REDUCTION_BILLIONS",
    "OVERSHOOT_ALLOWANCE",
    "RevenueCandidate",
    "compose_and_score",
    "reset_caches",
    "revenue_candidates",
    "revenue_target_billions",
    "top_quintile_burden_share",
]
