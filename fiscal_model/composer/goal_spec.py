"""
Structured fiscal goal specification — the contract between the natural-
language translation layer and the deterministic policy composer.

The translator (LLM or canned-philosophy fallback) produces a ``GoalSpec``;
the composer consumes it. Nothing downstream of this dataclass touches
free text, which keeps the composed mixes reproducible and shareable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Spending categories map onto PolicyType multipliers in the scoring engine.
SPENDING_CATEGORIES = (
    "infrastructure",
    "education",
    "healthcare",
    "defense",
    "safety_net",
    "climate",
    "research",
    "other",
)

REVENUE_PHILOSOPHIES = (
    "progressive",      # concentrate burden at the top (top rates, estate, NIIT)
    "broad_base",       # spread across most filers (all-bracket rates, expenditures)
    "corporate",        # corporate-side raisers (rate, CAMT, international)
    "mixed",            # blend of the above
)

DEFICIT_STANCES = (
    "neutral",          # revenue should roughly cover the new spending
    "reduce",           # raise more than is spent
    "invest",           # spending may exceed revenue raised
)


@dataclass(frozen=True)
class SpendingGoal:
    """One spending objective extracted from the user's description."""

    label: str                          # the user's words, e.g. "universal pre-K"
    category: str                       # one of SPENDING_CATEGORIES
    annual_billions: float | None = None  # None = unspecified; composer sizes it


@dataclass(frozen=True)
class GoalSpec:
    """Deterministic description of what the user wants a package to do."""

    revenue_philosophy: str             # one of REVENUE_PHILOSOPHIES
    deficit_stance: str                 # one of DEFICIT_STANCES
    spending_goals: tuple[SpendingGoal, ...] = ()
    # Free-text nuance the translator wants surfaced to the reader (never
    # parsed downstream), e.g. "user asked to avoid taxing under $400K".
    notes: str = ""
    # Optional hard floor from the user, e.g. "raise at least $1T".
    min_revenue_10yr_billions: float | None = None

    def validate(self) -> list[str]:
        """Return human-readable problems; empty when the spec is usable."""
        problems: list[str] = []
        if self.revenue_philosophy not in REVENUE_PHILOSOPHIES:
            problems.append(
                f"unknown revenue_philosophy {self.revenue_philosophy!r}"
            )
        if self.deficit_stance not in DEFICIT_STANCES:
            problems.append(f"unknown deficit_stance {self.deficit_stance!r}")
        for goal in self.spending_goals:
            if goal.category not in SPENDING_CATEGORIES:
                problems.append(
                    f"spending goal {goal.label!r} has unknown category "
                    f"{goal.category!r}"
                )
            if goal.annual_billions is not None and goal.annual_billions < 0:
                problems.append(
                    f"spending goal {goal.label!r} has negative size"
                )
        return problems


# Canned philosophies for the no-API-key fallback path. Each maps a short
# reader-facing label to a complete GoalSpec the composer can run as-is.
CANNED_GOAL_SPECS: dict[str, GoalSpec] = {
    "Progressive investment": GoalSpec(
        revenue_philosophy="progressive",
        deficit_stance="neutral",
        spending_goals=(
            SpendingGoal(label="Child care and pre-K", category="education",
                         annual_billions=40.0),
            SpendingGoal(label="Infrastructure", category="infrastructure",
                         annual_billions=60.0),
        ),
        notes="Fund family and infrastructure programs from high-income taxes.",
    ),
    "Deficit hawk": GoalSpec(
        revenue_philosophy="mixed",
        deficit_stance="reduce",
        spending_goals=(),
        notes="Reduce the deficit with a broad mix of revenue raisers.",
        min_revenue_10yr_billions=2_000.0,
    ),
    "Corporate-funded rebuild": GoalSpec(
        revenue_philosophy="corporate",
        deficit_stance="neutral",
        spending_goals=(
            SpendingGoal(label="Infrastructure", category="infrastructure",
                         annual_billions=80.0),
        ),
        notes="Pay for public investment from the corporate side.",
    ),
}


__all__ = [
    "CANNED_GOAL_SPECS",
    "DEFICIT_STANCES",
    "GoalSpec",
    "REVENUE_PHILOSOPHIES",
    "SPENDING_CATEGORIES",
    "SpendingGoal",
]
