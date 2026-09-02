"""
The values vector — the shared interlingua between "what a person believes"
and "which policies a deterministic selector picks".

``REDESIGN_PLAN.md`` §5b.2 names this the one validated dataclass used
everywhere. It is deliberately *small* and *continuous*: five dials, a list of
commitments the package must not violate, and the deficit target the package is
aiming at. Everything a reader can say about their fiscal philosophy has to
survive the trip through these seven fields, because the architecture rule is
that the LLM only ever produces one of these — it never picks a policy.

    free text ──(translate.translate_values_text: the ONLY LLM call)──▶ ValuesVector
    archetype ──(archetypes.yaml, no LLM at all)───────────────────────▶ ValuesVector
    ValuesVector ──(composer.select_package: pure, tags × vector)──────▶ [(policy_id, why)]

:class:`~fiscal_model.composer.goal_spec.GoalSpec` predates this module (it is
the Package Studio contract, #65) and survives as a thin adapter in both
directions — :meth:`ValuesVector.to_goal_spec` and :func:`from_goal_spec` — so
``composer.compose_and_score`` and its 27 tests keep working unchanged.

Sign conventions, stated once:

* ``redistribution``   −1 = burden should not be concentrated at the top …
                       +1 = judge the budget by what it does for the worst-off.
* ``govt_size``        −1 = a smaller state, +1 = a larger one. This is about
                       the *level* of government, not about the deficit.
* ``deficit_concern``   0 = the deficit is not what I am optimising …
                        1 = closing it is the point.
* ``growth_priority``   0 = growth effects do not drive my choices …
                        1 = pick the instruments with the lowest growth cost.
* ``generational_weight`` 0 = weigh today's cohorts …
                        1 = weigh future cohorts equally with today's.
* ``target_pct_gdp``   the deficit the package is aiming at, in % of GDP —
                       the same number the Build target slider carries.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any

# ── Dimensions ──────────────────────────────────────────────────────────
#: name -> (minimum, maximum). The signed dials run −1..1, the intensities 0..1.
DIMENSION_BOUNDS: dict[str, tuple[float, float]] = {
    "redistribution": (-1.0, 1.0),
    "deficit_concern": (0.0, 1.0),
    "govt_size": (-1.0, 1.0),
    "growth_priority": (0.0, 1.0),
    "generational_weight": (0.0, 1.0),
}

#: Reader-facing names, in the order the reflection panel renders them.
DIMENSION_LABELS: dict[str, str] = {
    "redistribution": "Redistribution",
    "deficit_concern": "Deficit concern",
    "govt_size": "Size of government",
    "growth_priority": "Growth priority",
    "generational_weight": "Generational weight",
}

#: The Build target slider's own range (``deficit_target.py``: 0–6%, step 0.5).
TARGET_PCT_GDP_BOUNDS: tuple[float, float] = (0.0, 6.0)
DEFAULT_TARGET_PCT_GDP = 3.0


# ── Protected commitments ───────────────────────────────────────────────
#
# "Protected" is a *veto*, not a preference: a policy that touches a protected
# commitment is removed from the candidate set before scoring, however well it
# would otherwise align. Two rules keep the vetoes honest:
#
# 1. **Only the burden side is vetoed.** Protection excludes policies that
#    *raise* the burden on a group (a tax rise, a benefit cut), never policies
#    that lower it. Protecting middle-class rates cannot rule out a middle-class
#    tax cut.
# 2. **Vetoes are read off the catalog's own tags** wherever tags are precise
#    enough, with an explicit id list only where they are not. Both halves are
#    data, so the mapping is inspectable and testable rather than hidden in UI
#    code.
#
# Where today's catalog contains nothing a commitment would veto, that is
# recorded as an empty veto and said out loud in the UI rather than quietly
# implying the constraint bit. ``ss_benefits`` and ``defense`` are both in that
# position: the Build catalog scores no Social-Security benefit cut and no
# defense-spending cut. They stay in the vocabulary because readers say them,
# and because the veto will bite the moment such an option is scored.

#: Directions that *raise* someone's burden — the only ones a veto can catch.
_BURDEN_DIRECTIONS = frozenset({"raise_revenue", "cut_spending"})


@dataclass(frozen=True)
class ProtectedRule:
    """One commitment: what it means, and which policies it vetoes."""

    key: str
    label: str                      # reader-facing, for the multiselect
    #: A second-person statement, joined into the "why" sentence by
    #: ``composer._protected_contrast``: "…, which is off the table because
    #: {clause}". Write it as a statement ("you protected X"), never as a bare
    #: relative clause — the connective is the caller's job.
    clause: str
    #: Tag predicate, expressed as data: every listed tag must match one of the
    #: allowed values, and ``direction`` must be a burden direction.
    tag_any: tuple[tuple[str, tuple[str, ...]], ...] = ()
    #: Explicit ids, for instruments the five tags cannot single out.
    ids: frozenset[str] = frozenset()

    def vetoes(self, policy_id: str, tags: Mapping[str, str]) -> bool:
        """True when this commitment rules the policy out."""
        if policy_id in self.ids:
            return True
        if not self.tag_any:
            return False
        if str(tags.get("direction", "")) not in _BURDEN_DIRECTIONS:
            return False
        return all(
            str(tags.get(tag_name, "")) in allowed for tag_name, allowed in self.tag_any
        )


PROTECTED_RULES: tuple[ProtectedRule, ...] = (
    ProtectedRule(
        key="middle_class_rates",
        label="Middle-class rates",
        clause="you protected middle-class rates",
        # A raiser reaches below the top brackets when it taxes consumption
        # (tariffs, a carbon tax) or broadens an individual base whose
        # incidence the engine calls neutral or regressive.
        tag_any=(
            ("base", ("consumption", "individual")),
            ("progressivity", ("neutral", "regressive")),
        ),
    ),
    ProtectedRule(
        key="ss_benefits",
        label="Social Security benefits",
        clause="you protected Social Security benefits",
        # A benefit cut on the payroll-financed side. Vacuous in today's
        # catalog — no scored option cuts SS benefits — and said so in the UI.
        tag_any=(("base", ("payroll",)), ("direction", ("cut_spending",))),
    ),
    ProtectedRule(
        key="medicare",
        label="Medicare and health coverage",
        clause="you protected health coverage",
        # Outlay-side savings taken out of health programs, including the
        # drug-pricing options. Conservative on purpose: a reader who says
        # "don't touch Medicare" is not asking us to judge which cuts are
        # painless.
        tag_any=(("base", ("transfer",)), ("direction", ("cut_spending",))),
    ),
    ProtectedRule(
        key="safety_net",
        label="Safety-net transfers",
        clause="you protected safety-net transfers",
        tag_any=(
            ("base", ("transfer",)),
            ("progressivity", ("regressive",)),
            ("direction", ("cut_spending",)),
        ),
    ),
    ProtectedRule(
        key="defense",
        label="Defense spending",
        clause="you protected defense",
        # No scored defense-spending cut in today's catalog; see the note above.
        tag_any=(("base", ("defense",)), ("direction", ("cut_spending",))),
    ),
    ProtectedRule(
        key="clean_energy_credits",
        label="Clean-energy incentives",
        clause="you protected clean-energy incentives",
        # The five tags cannot separate "repeal a credit" from "tax the thing
        # the credit subsidises", so these two are named outright.
        ids=frozenset({"ira-clean-energy-repeal", "ev-credit-repeal"}),
    ),
    ProtectedRule(
        key="corporate_investment",
        label="Investment incentives",
        clause="you protected investment incentives",
        tag_any=(("base", ("corporate",)), ("direction", ("raise_revenue",))),
    ),
)

PROTECTED_RULE_BY_KEY: dict[str, ProtectedRule] = {
    rule.key: rule for rule in PROTECTED_RULES
}
PROTECTED_KEYS: tuple[str, ...] = tuple(PROTECTED_RULE_BY_KEY)
PROTECTED_LABELS: dict[str, str] = {
    rule.key: rule.label for rule in PROTECTED_RULES
}


def vetoing_rules(
    policy_id: str,
    tags: Mapping[str, str],
    protected: Iterable[str],
) -> tuple[ProtectedRule, ...]:
    """Every protected commitment that rules this policy out, in schema order."""
    wanted = {str(key) for key in protected}
    return tuple(
        rule
        for rule in PROTECTED_RULES
        if rule.key in wanted and rule.vetoes(policy_id, tags)
    )


# ── The vector ──────────────────────────────────────────────────────────
def _clamp(value: Any, low: float, high: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:  # NaN
        return default
    return max(low, min(high, number))


@dataclass(frozen=True)
class ValuesVector:
    """A fiscal philosophy, in seven fields. See the module docstring."""

    redistribution: float = 0.0
    deficit_concern: float = 0.5
    govt_size: float = 0.0
    growth_priority: float = 0.5
    generational_weight: float = 0.5
    protected: tuple[str, ...] = ()
    target_pct_gdp: float = DEFAULT_TARGET_PCT_GDP

    # -- validation ------------------------------------------------------
    def validate(self) -> list[str]:
        """Human-readable problems; empty when the vector is usable."""
        problems: list[str] = []
        for name, (low, high) in DIMENSION_BOUNDS.items():
            value = getattr(self, name)
            try:
                number = float(value)
            except (TypeError, ValueError):
                problems.append(f"{name} is not a number ({value!r})")
                continue
            if number != number or not (low <= number <= high):
                problems.append(f"{name} must be between {low} and {high}, got {value!r}")
        low, high = TARGET_PCT_GDP_BOUNDS
        try:
            target = float(self.target_pct_gdp)
        except (TypeError, ValueError):
            problems.append(f"target_pct_gdp is not a number ({self.target_pct_gdp!r})")
        else:
            if target != target or not (low <= target <= high):
                problems.append(
                    f"target_pct_gdp must be between {low} and {high}, "
                    f"got {self.target_pct_gdp!r}"
                )
        for key in self.protected:
            if key not in PROTECTED_RULE_BY_KEY:
                problems.append(f"unknown protected commitment {key!r}")
        return problems

    def clamped(self) -> ValuesVector:
        """A copy with every field coerced into range and deduplicated.

        Selection must never depend on whether a caller remembered to
        validate, so :func:`~fiscal_model.composer.composer.select_package`
        clamps on the way in. Clamping is idempotent.
        """
        seen: list[str] = []
        for key in self.protected or ():
            token = str(key).strip()
            if token in PROTECTED_RULE_BY_KEY and token not in seen:
                seen.append(token)
        return replace(
            self,
            redistribution=_clamp(self.redistribution, -1.0, 1.0, 0.0),
            deficit_concern=_clamp(self.deficit_concern, 0.0, 1.0, 0.5),
            govt_size=_clamp(self.govt_size, -1.0, 1.0, 0.0),
            growth_priority=_clamp(self.growth_priority, 0.0, 1.0, 0.5),
            generational_weight=_clamp(self.generational_weight, 0.0, 1.0, 0.5),
            protected=tuple(
                key for key in PROTECTED_KEYS if key in seen
            ),  # schema order, so the same set always serialises identically
            target_pct_gdp=_clamp(
                self.target_pct_gdp, *TARGET_PCT_GDP_BOUNDS, DEFAULT_TARGET_PCT_GDP
            ),
        )

    # -- serialisation ---------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict, key order fixed so encodings are stable."""
        vector = self.clamped()
        payload: dict[str, Any] = {
            name: round(float(getattr(vector, name)), 4) for name in DIMENSION_BOUNDS
        }
        payload["protected"] = list(vector.protected)
        payload["target_pct_gdp"] = round(float(vector.target_pct_gdp), 4)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any] | None) -> ValuesVector:
        """Tolerant reader: unknown keys ignored, bad numbers fall to defaults."""
        data = dict(payload or {})
        raw_protected = data.get("protected") or ()
        if isinstance(raw_protected, str):
            raw_protected = [
                token.strip() for token in raw_protected.split(",") if token.strip()
            ]
        return cls(
            redistribution=_clamp(data.get("redistribution"), -1.0, 1.0, 0.0),
            deficit_concern=_clamp(data.get("deficit_concern"), 0.0, 1.0, 0.5),
            govt_size=_clamp(data.get("govt_size"), -1.0, 1.0, 0.0),
            growth_priority=_clamp(data.get("growth_priority"), 0.0, 1.0, 0.5),
            generational_weight=_clamp(data.get("generational_weight"), 0.0, 1.0, 0.5),
            protected=tuple(str(key) for key in raw_protected),
            target_pct_gdp=_clamp(
                data.get("target_pct_gdp"), *TARGET_PCT_GDP_BOUNDS, DEFAULT_TARGET_PCT_GDP
            ),
        ).clamped()

    def to_base64(self) -> str:
        """URL-safe base64 of the canonical JSON — the ``?vector=`` payload."""
        blob = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return base64.urlsafe_b64encode(blob.encode("utf-8")).decode("ascii").rstrip("=")

    @classmethod
    def from_base64(cls, token: Any) -> ValuesVector | None:
        """Inverse of :meth:`to_base64`; ``None`` for anything unreadable."""
        text = str(token or "").strip()
        if not text:
            return None
        padded = text + "=" * (-len(text) % 4)
        try:
            payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return cls.from_dict(payload)

    # -- GoalSpec adapter ------------------------------------------------
    def to_goal_spec(self) -> Any:
        """Project onto the Package Studio :class:`GoalSpec` contract.

        Lossy by construction — ``GoalSpec`` is categorical where the vector is
        continuous — but it keeps ``composer.compose_and_score`` (the deep,
        live-scored path) reachable from a values vector without a second
        translation step.
        """
        from .goal_spec import GoalSpec

        if self.redistribution >= 0.45:
            philosophy = "progressive"
        elif self.redistribution <= -0.25:
            philosophy = "broad_base"
        else:
            philosophy = "mixed"

        if self.deficit_concern >= 0.6:
            stance = "reduce"
        elif self.govt_size >= 0.45:
            stance = "invest"
        else:
            stance = "neutral"

        notes = describe(self)
        return GoalSpec(
            revenue_philosophy=philosophy,
            deficit_stance=stance,
            spending_goals=(),
            notes=notes,
        )


def from_goal_spec(spec: Any) -> ValuesVector:
    """The other half of the adapter: a ``GoalSpec`` read as a values vector."""
    philosophy = str(getattr(spec, "revenue_philosophy", "") or "mixed")
    stance = str(getattr(spec, "deficit_stance", "") or "neutral")
    redistribution = {
        "progressive": 0.8,
        "corporate": 0.5,
        "mixed": 0.0,
        "broad_base": -0.4,
    }.get(philosophy, 0.0)
    deficit_concern = {"reduce": 0.9, "neutral": 0.5, "invest": 0.2}.get(stance, 0.5)
    govt_size = {"reduce": -0.2, "neutral": 0.0, "invest": 0.5}.get(stance, 0.0)
    if getattr(spec, "spending_goals", ()):
        govt_size = max(govt_size, 0.4)
    return ValuesVector(
        redistribution=redistribution,
        deficit_concern=deficit_concern,
        govt_size=govt_size,
        growth_priority=0.5,
        generational_weight=0.5,
        protected=(),
        target_pct_gdp=DEFAULT_TARGET_PCT_GDP,
    ).clamped()


# ── Reader-facing description ───────────────────────────────────────────
_SCALE_WORDS: tuple[tuple[float, str], ...] = (
    (-0.6, "Strongly against"),
    (-0.2, "Leaning against"),
    (0.2, "Neutral"),
    (0.6, "Leaning toward"),
    (1.01, "Strong"),
)

#: Per-dimension wording, so "Strong" reads as the right kind of strong.
_DIMENSION_WORDS: dict[str, tuple[str, ...]] = {
    # ordered low → high, five bands matching _SCALE_WORDS
    "redistribution": ("Flat", "Light", "Mixed", "Progressive", "Strong"),
    "deficit_concern": ("Not a priority", "Low", "Moderate", "High", "Overriding"),
    "govt_size": ("Much smaller", "Smaller", "Neutral", "Larger", "Much larger"),
    "growth_priority": ("Not a priority", "Low", "Moderate", "High", "Overriding"),
    "generational_weight": ("Today first", "Low", "Balanced", "High", "Future first"),
}


def band(name: str, value: float) -> str:
    """The word the reflection panel shows next to a dial."""
    words = _DIMENSION_WORDS.get(name)
    if not words:
        return f"{value:+.2f}"
    low, high = DIMENSION_BOUNDS.get(name, (-1.0, 1.0))
    span = high - low or 1.0
    # Five equal bands across the dimension's own range.
    index = int(min(4, max(0, (float(value) - low) / span * 5)))
    return words[index]


def describe(vector: ValuesVector) -> str:
    """One-line rendering of a vector, for notes and export headers."""
    parts = [
        f"{DIMENSION_LABELS[name]}: {band(name, float(getattr(vector, name)))}"
        for name in DIMENSION_BOUNDS
    ]
    if vector.protected:
        parts.append(
            "Protected: "
            + ", ".join(PROTECTED_LABELS[key].lower() for key in vector.protected)
        )
    parts.append(f"target {float(vector.target_pct_gdp):.1f}% of GDP")
    return "; ".join(parts)


__all__ = [
    "DEFAULT_TARGET_PCT_GDP",
    "DIMENSION_BOUNDS",
    "DIMENSION_LABELS",
    "PROTECTED_KEYS",
    "PROTECTED_LABELS",
    "PROTECTED_RULES",
    "PROTECTED_RULE_BY_KEY",
    "TARGET_PCT_GDP_BOUNDS",
    "ProtectedRule",
    "ValuesVector",
    "band",
    "describe",
    "from_goal_spec",
    "vetoing_rules",
]
