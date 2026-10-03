"""Which of a Build package's list prices can be added, and which cannot.

The Build page quotes **official list prices** and sums them. That sum is exact
only when the selected policies do not touch each other's tax base, and the
page used to say so with one blanket sentence ("interactions are not modeled")
that read the same for a package of two unrelated items and for a package whose
two members demonstrably overlap. This module replaces the blanket sentence
with a classification of the package, and adds -- optionally, lazily -- a
measured size for the one family of overlaps the repository's CPS microsim can
actually price.

**What this module does not do.** It never changes a list price and never
changes ``sum(catalog[bid].score ...)``. Build does not call the scorer, and
nothing here lets it start. The classification is a *disclosure*; the measured
share is an *approximation shown beside the total*, never folded into it.

Three honest tiers of claim, in the order the evidence runs out:

``interacting`` (and, once measured, ``interacting_measured``)
    The pair's reforms move the same base inside ``MicroTaxCalculator`` -- an
    ordinary-rate change and a SALT / standard-deduction change are the case
    that matters (the SALT-cap reform changes taxable income, and a rate change
    is a rate on taxable income). Those can be priced jointly on the CPS
    microsim and the interaction reported as a **share** of each member's own
    standalone yield. Shares, not dollars: the microsim's levels sit 3-4x
    below the official list prices (it is a CPS file, with the SOI top tail
    appended), so a dollar interaction from it would be quoted beside a list
    price it is not on the scale of.

``structurally_additive``
    The calculator composes the pair additively **by construction** -- an
    ordinary-rate change is added to the result *after* ``calculate`` has run,
    so it cannot see an AMT exemption or a credit schedule, and two credits'
    schedules are computed independently. That is a fact about the code, not a
    measurement, and is labelled as one: a zero from a post-hoc adder says
    nothing about whether the real provisions interact.

``additive_only_unmodelled``
    Everything else -- corporate, estate, payroll, tariffs, the TCJA
    composite, most tax expenditures, drug pricing, the ACA credit,
    enforcement. ``policy_to_microsim_reforms`` returns ``{}`` for these on
    purpose, so there is nothing to measure with. The package says so and, where
    two members share a channel (two corporate-base items, say), names the pair.

Nothing here invents a model constant. The classification table is a statement
about which channel each policy acts on; the only numbers are those the
microsim produces from reforms ``policy_to_microsim_reforms`` already builds.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import combinations
from typing import Any

# ── Statuses ─────────────────────────────────────────────────────────────
STATUS_SINGLE = "single"
STATUS_NO_OVERLAP = "no_overlap"
STATUS_STRUCTURALLY_ADDITIVE = "structurally_additive"
STATUS_INTERACTING_UNMEASURED = "interacting_unmeasured"
STATUS_INTERACTING_MEASURED = "interacting_measured"
STATUS_ADDITIVE_ONLY_UNMODELLED = "additive_only_unmodelled"

#: Every value ``PackageInteractionReport.status`` can take. The first, third,
#: fifth and sixth are the four a reader of the brief expects; ``unmeasured``
#: exists because "this pair interacts and can be measured" is a different
#: sentence from "this pair was measured", and the page must not say the
#: second when only the first is true.
STATUSES: tuple[str, ...] = (
    STATUS_SINGLE,
    STATUS_NO_OVERLAP,
    STATUS_STRUCTURALLY_ADDITIVE,
    STATUS_INTERACTING_UNMEASURED,
    STATUS_INTERACTING_MEASURED,
    STATUS_ADDITIVE_ONLY_UNMODELLED,
)

# ── Pair kinds ───────────────────────────────────────────────────────────
KIND_NO_OVERLAP = "no_overlap"
KIND_STRUCTURALLY_ADDITIVE = "structurally_additive"
KIND_INTERACTING = "interacting"
KIND_UNMODELLED = "unmodelled"
KIND_INCONSISTENT_PRICE = "inconsistent_list_price"

# ── Channels ─────────────────────────────────────────────────────────────
#: Channels the CPS microsim can express (``policy_to_microsim_reforms``).
ORDINARY_RATE = "ordinary_rate"
SALT_ITEMIZATION = "salt_itemization"
STD_DEDUCTION = "std_deduction"
AMT_EXEMPTION = "amt_exemption"
REFUNDABLE_CREDIT = "refundable_credit"
MICROSIM_CHANNELS: frozenset[str] = frozenset(
    {ORDINARY_RATE, SALT_ITEMIZATION, STD_DEDUCTION, AMT_EXEMPTION, REFUNDABLE_CREDIT}
)

_TCJA_COMPOSITE = frozenset(
    {
        "tcja_composite",
        ORDINARY_RATE,
        STD_DEDUCTION,
        SALT_ITEMIZATION,
        AMT_EXEMPTION,
        REFUNDABLE_CREDIT,
        "estate",
    }
)

#: ``build_id -> channels the policy acts on``. Hand-kept on purpose: it is a
#: claim about each policy's mechanism, and a test fails if a catalog id has no
#: entry, so a new Build option cannot arrive with no answer to "what does it
#: touch". A *channel* is a base or instrument, not a policy area -- the
#: mortgage deduction and the SALT cap share ``salt_itemization`` because both
#: decide who itemizes.
INTERACTION_CHANNELS: dict[str, frozenset[str]] = {
    # TCJA composites (several instruments at once; no microsim path)
    "tcja-full-extension": _TCJA_COMPOSITE,
    "tcja-extension-no-salt-cap": _TCJA_COMPOSITE,
    "tcja-rates-only": frozenset({"tcja_composite", ORDINARY_RATE}),
    # Corporate
    "corporate-28pct": frozenset({"corporate"}),
    "corporate-15pct": frozenset({"corporate"}),
    # Credits
    "ctc-expansion-2021": frozenset({REFUNDABLE_CREDIT}),
    "ctc-extension": frozenset({REFUNDABLE_CREDIT}),
    "eitc-childless-expansion": frozenset({REFUNDABLE_CREDIT}),
    # Estate
    "estate-extend-tcja": frozenset({"estate"}),
    "estate-exemption-3-5m": frozenset({"estate"}),
    "estate-repeal": frozenset({"estate"}),
    # Payroll
    "ss-cap-90pct": frozenset({"payroll"}),
    "ss-donut-250k": frozenset({"payroll"}),
    "ss-cap-eliminate": frozenset({"payroll"}),
    "niit-expand": frozenset({"payroll"}),
    # AMT
    "amt-extend-tcja-relief": frozenset({AMT_EXEMPTION}),
    "amt-repeal-individual": frozenset({AMT_EXEMPTION}),
    "amt-repeal-corporate": frozenset({"corporate"}),
    # Health
    "aca-ptc-extend-enhanced": frozenset({"health_credit"}),
    "aca-ptc-repeal": frozenset({"health_credit"}),
    "cap-employer-health-exclusion": frozenset({"employer_health"}),
    # Itemised deductions and other tax expenditures
    "mortgage-deduction-eliminate": frozenset({SALT_ITEMIZATION}),
    "salt-cap-repeal": frozenset({SALT_ITEMIZATION}),
    "salt-deduction-eliminate": frozenset({SALT_ITEMIZATION}),
    "charitable-deduction-cap": frozenset({SALT_ITEMIZATION}),
    "step-up-basis-eliminate": frozenset({"capital_gains", "estate"}),
    # Ordinary rates
    "top-rate-39-6": frozenset({ORDINARY_RATE}),
    # International (acts on the corporate base)
    "gilti-reform": frozenset({"corporate", "international"}),
    "fdii-repeal": frozenset({"corporate", "international"}),
    "pillar-two-adoption": frozenset({"corporate", "international"}),
    "international-package": frozenset({"corporate", "international"}),
    # Enforcement, drug pricing
    "irs-enforcement-ira": frozenset({"enforcement"}),
    "irs-enforcement-double": frozenset({"enforcement"}),
    "drug-negotiation-expand": frozenset({"drug_pricing"}),
    "insulin-cap-universal": frozenset({"drug_pricing"}),
    "drug-reference-pricing": frozenset({"drug_pricing"}),
    # Tariffs
    "tariff-universal-10pct": frozenset({"tariff"}),
    "tariff-china-60pct": frozenset({"tariff"}),
    "tariff-auto-25pct": frozenset({"tariff"}),
    "tariff-steel-aluminum-25pct": frozenset({"tariff"}),
    "tariff-reciprocal": frozenset({"tariff"}),
    # Climate / energy
    "ira-clean-energy-repeal": frozenset({"climate_credits"}),
    "carbon-tax-50": frozenset({"carbon_tax"}),
    "ev-credit-repeal": frozenset({"climate_credits"}),
}

#: Build ids whose reform ``policy_to_microsim_reforms`` can express today.
#: Static so ``classify_package`` stays cheap; a test pins it to what the
#: function actually returns, so it cannot drift from the code it describes.
MICROSIM_MEASURABLE_IDS: frozenset[str] = frozenset(
    {"top-rate-39-6", "salt-cap-repeal", "eitc-childless-expansion"}
)

#: Channel pairs the calculator composes additively *by construction* (an
#: ordinary-rate change is added after ``calculate``; two credits' schedules
#: are computed independently). Unordered.
_STRUCTURALLY_ADDITIVE: frozenset[frozenset[str]] = frozenset(
    {
        frozenset({ORDINARY_RATE}),  # two rate changes: both post-hoc adders
        frozenset({ORDINARY_RATE, AMT_EXEMPTION}),
        frozenset({ORDINARY_RATE, REFUNDABLE_CREDIT}),
        frozenset({REFUNDABLE_CREDIT}),
    }
)

#: Channel pairs that change the same base inside the calculator, so the joint
#: score is not the sum. Unordered. The first two rows carry the evidence in
#: this module's tests; the rest follow from the same mechanism (a deduction,
#: the AMT exemption and the standard deduction all enter taxable income or the
#: AMT preference add-back together).
_INTERACTING: frozenset[frozenset[str]] = frozenset(
    {
        frozenset({ORDINARY_RATE, SALT_ITEMIZATION}),
        frozenset({ORDINARY_RATE, STD_DEDUCTION}),
        frozenset({SALT_ITEMIZATION, STD_DEDUCTION}),
        frozenset({SALT_ITEMIZATION, AMT_EXEMPTION}),
        frozenset({STD_DEDUCTION, AMT_EXEMPTION}),
        frozenset({REFUNDABLE_CREDIT, STD_DEDUCTION}),
    }
)

# ── Reform families (the clash guard) ────────────────────────────────────
#: Keys one ``apply_reform`` call applies *in sequence*, so a later reform in
#: the same family silently overrides or re-bases an earlier one. Two reforms
#: touching one family are one instrument set twice, not two policies, and the
#: joint score of that is not defined -- refuse rather than return a number
#: that is just whichever reform came second.
_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ctc", ("ctc_", "actc_")),
    ("eitc", ("eitc_",)),
    ("rebate", ("rebate_",)),
    ("rates", ("rate_changes", "new_top_rate")),
    ("salt", ("salt_cap",)),
    ("std_deduction", ("std_deduction",)),
    ("amt", ("amt_",)),
)

#: The one family that *is* composed rather than refused: an ordinary-rate
#: ``income_rate_change`` tranche is a linear add-on, so two of them stack as
#: separate tranches and the joint is exactly the sum.
_TRANCHE_KEYS = ("income_rate_change", "income_rate_change_threshold")


class ReformClashError(ValueError):
    """Two reforms set the same instrument, so ``apply_reform`` would let one win."""


def _family_of(key: str) -> str | None:
    for family, prefixes in _FAMILIES:
        if key.startswith(prefixes):
            return family
    return None


def _families(reform: Mapping[str, Any]) -> set[str]:
    return {f for f in (_family_of(k) for k in reform) if f is not None}


def merge_reforms(
    reforms: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[tuple[float, float]]]:
    """Merge reform dicts for one joint ``apply_reform`` call.

    Returns ``(merged, tranches)``: the merged dict (carrying at most one
    ordinary-rate tranche) and the *remaining* ``(threshold, rate)`` tranches
    to be added afterwards, exactly as the engine adds its own. Raises
    :class:`ReformClashError` when two reforms touch the same key or the same
    reform family, because ``apply_reform`` would then apply them in sequence
    and the later one would win.
    """
    merged: dict[str, Any] = {}
    claimed_families: dict[str, int] = {}
    tranches: list[tuple[float, float]] = []

    for index, reform in enumerate(reforms):
        for key, value in reform.items():
            if key in _TRANCHE_KEYS:
                continue
            if key in merged:
                raise ReformClashError(f"both reforms set {key!r}")
            merged[key] = value
        for family in _families({k: v for k, v in reform.items() if k not in _TRANCHE_KEYS}):
            owner = claimed_families.setdefault(family, index)
            if owner != index:
                raise ReformClashError(f"both reforms set the {family!r} instrument")
        if "income_rate_change" in reform:
            tranches.append(
                (
                    float(reform.get("income_rate_change_threshold", 0.0) or 0.0),
                    float(reform["income_rate_change"]),
                )
            )

    # Canonical order so the result cannot depend on argument order.
    tranches.sort()
    if tranches:
        first_threshold, first_rate = tranches[0]
        merged["income_rate_change"] = first_rate
        merged["income_rate_change_threshold"] = first_threshold
    return merged, tranches[1:]


# ── The microsim (lazy; everything below is only reached on demand) ──────
@lru_cache(maxsize=1)
def _population() -> Any:
    """CPS tax units + SOI top tail + imputed SALT, built once per process."""
    import pandas as pd

    from fiscal_model.feasibility import DEFAULT_MICRODATA_RELATIVE_PATH
    from fiscal_model.microsim.salt_imputation import impute_salt_and_itemized
    from fiscal_model.microsim.top_tail import augment_top_tail

    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / DEFAULT_MICRODATA_RELATIVE_PATH
    raw = pd.read_csv(path)
    augmented, _report = augment_top_tail(raw, year=2023)
    return impute_salt_and_itemized(augmented).copy()


@lru_cache(maxsize=1)
def _baseline_final_tax() -> Any:
    from fiscal_model.microsim.engine import MicroTaxCalculator

    base = MicroTaxCalculator(2025).calculate(_population())
    return base["final_tax"].values.copy()


def joint_tax_change(reforms: Sequence[Mapping[str, Any]]) -> float:
    """Annual change in final tax, $B, microsim levels (+ = revenue).

    One ``apply_reform`` call for the merged reform plus any extra ordinary-rate
    tranches added the way the engine adds its own. Raises
    :class:`ReformClashError` on a clash.
    """
    import numpy as np

    from fiscal_model.microsim.engine import MicroTaxCalculator

    merged, extra = merge_reforms(reforms)
    pop = _population()
    calc = MicroTaxCalculator(2025)
    result = calc.apply_reform(pop, merged)
    final_tax = result["final_tax"].values.copy()
    if extra:
        taxable = result["taxable_income"].values
        pref = np.minimum(calc.preferential_income(result), np.maximum(0, taxable))
        ordinary = np.maximum(0, taxable - pref)
        for threshold, rate in extra:
            final_tax += np.maximum(0, ordinary - threshold) * rate
    weights = pop["weight"].values
    return float(((final_tax - _baseline_final_tax()) * weights).sum() / 1e9)


@dataclass(frozen=True)
class InteractionMeasurement:
    """A measured pairwise interaction on the CPS microsim.

    ``a`` and ``b`` are ordered ``a < b`` so the object is the same whichever
    way the pair was asked. ``standalone_*``, ``joint`` and ``interaction`` are
    **microsim-level annual $B, revenue convention** and are *not* on the scale
    of the Build page's list prices (the microsim runs 3-4x below them); only
    the shares are meant to be shown. ``share_of_*`` is the interaction as a
    fraction of that member's own ``abs(standalone)`` yield: negative means the
    pair raises less revenue than its two standalone scores summed.
    """

    a: str
    b: str
    standalone_a: float
    standalone_b: float
    joint: float
    interaction: float
    share_of_a: float | None
    share_of_b: float | None
    #: The member the headline share is quoted against: the rate item when
    #: exactly one member is an ordinary-rate change, else the larger yield.
    reference: str

    @property
    def share(self) -> float | None:
        return self.share_of_a if self.reference == self.a else self.share_of_b


def _share(interaction: float, standalone: float) -> float | None:
    if abs(standalone) < 1e-12:
        return None
    return interaction / abs(standalone)


@lru_cache(maxsize=None)
def microsim_reform(build_id: str) -> tuple[tuple[str, Any], ...]:
    """The member's ``policy_to_microsim_reforms`` dict as a hashable tuple.

    ``()`` when the policy has no microsim path (or no preset to build one
    from). Built only through the repository's own function; nothing here
    translates a policy itself.
    """
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.composer.composer import _build_preset_policy
    from fiscal_model.distribution_effects import policy_to_microsim_reforms
    from fiscal_model.preset_ids import preset_id_for_token

    label = next(
        (k for k in PRESET_POLICIES if preset_id_for_token(k) == build_id), None
    )
    if label is None:
        return ()
    policy, _ = _build_preset_policy(label, PRESET_POLICIES[label])
    return tuple(sorted(policy_to_microsim_reforms(policy).items()))


def measure_reforms(
    a_id: str,
    reform_a: Mapping[str, Any],
    b_id: str,
    reform_b: Mapping[str, Any],
) -> InteractionMeasurement | None:
    """Measure the interaction between two explicit reform dicts.

    ``None`` when either reform is empty (nothing to measure with) or the two
    clash (see :func:`merge_reforms`). The pair is canonicalised, so
    ``measure_reforms(a, ra, b, rb) == measure_reforms(b, rb, a, ra)``.
    """
    if not reform_a or not reform_b:
        return None
    if b_id < a_id:
        a_id, reform_a, b_id, reform_b = b_id, reform_b, a_id, reform_a
    try:
        joint = joint_tax_change([reform_a, reform_b])
    except ReformClashError:
        return None
    alone_a = joint_tax_change([reform_a])
    alone_b = joint_tax_change([reform_b])
    interaction = joint - (alone_a + alone_b)
    a_is_rate = "income_rate_change" in reform_a or "new_top_rate" in reform_a
    b_is_rate = "income_rate_change" in reform_b or "new_top_rate" in reform_b
    if a_is_rate != b_is_rate:
        reference = a_id if a_is_rate else b_id
    else:
        reference = a_id if abs(alone_a) >= abs(alone_b) else b_id
    return InteractionMeasurement(
        a=a_id,
        b=b_id,
        standalone_a=alone_a,
        standalone_b=alone_b,
        joint=joint,
        interaction=interaction,
        share_of_a=_share(interaction, alone_a),
        share_of_b=_share(interaction, alone_b),
        reference=reference,
    )


@lru_cache(maxsize=256)
def _measured_sorted(a: str, b: str) -> InteractionMeasurement | None:
    return measure_reforms(a, dict(microsim_reform(a)), b, dict(microsim_reform(b)))


def measured_interaction_share(a: str, b: str) -> InteractionMeasurement | None:
    """Score ``a``, ``b`` and ``a+b`` on the CPS microsim; interaction as shares.

    Built only from ``policy_to_microsim_reforms`` (via :func:`microsim_reform`),
    ``MicroTaxCalculator.apply_reform`` and ``augment_top_tail``. Returns
    ``None`` -- never a guess -- when either member has no microsim reform or
    the two reforms clash on one instrument. Cached; symmetric in its
    arguments. Slow on first call (population build), cheap after.
    """
    first, second = sorted((a, b))
    if first == second:
        return None
    return _measured_sorted(first, second)


def measure_package(selection: Iterable[str]) -> dict[tuple[str, str], InteractionMeasurement]:
    """Measure every pair in ``selection`` that is classed ``interacting``."""
    report = classify_package(selection)
    found: dict[tuple[str, str], InteractionMeasurement] = {}
    for finding in report.findings:
        if finding.kind == KIND_INTERACTING and finding.measurable:
            measurement = measured_interaction_share(finding.a, finding.b)
            if measurement is not None:
                found[(finding.a, finding.b)] = measurement
    return found


# ── Classification (pure, cheap, deterministic) ──────────────────────────
@dataclass(frozen=True)
class PairFinding:
    """One statement about one pair of selected policies. ``a < b`` always."""

    a: str
    b: str
    kind: str
    reason: str
    shared_channels: tuple[str, ...] = ()
    #: Both members have a microsim reform, so the interaction can be measured.
    measurable: bool = False
    measurement: InteractionMeasurement | None = None


@dataclass(frozen=True)
class PackageInteractionReport:
    """How far the package's summed list prices can be trusted as a joint score."""

    status: str
    #: The selection, sorted: the report is the same whichever order it was built in.
    selection: tuple[str, ...]
    findings: tuple[PairFinding, ...] = field(default_factory=tuple)
    #: Plain-English names for ids, as supplied by the caller's catalog.
    names: Mapping[str, str] = field(default_factory=dict)

    def name(self, build_id: str) -> str:
        return self.names.get(build_id, build_id)

    def pair_name(self, finding: PairFinding) -> str:
        return f"{self.name(finding.a)} × {self.name(finding.b)}"

    def of_kind(self, kind: str) -> tuple[PairFinding, ...]:
        return tuple(f for f in self.findings if f.kind == kind)

    @property
    def interacting(self) -> tuple[PairFinding, ...]:
        return self.of_kind(KIND_INTERACTING)

    @property
    def measurable(self) -> tuple[PairFinding, ...]:
        return tuple(f for f in self.interacting if f.measurable)

    @property
    def inconsistent(self) -> tuple[PairFinding, ...]:
        return self.of_kind(KIND_INCONSISTENT_PRICE)

    @property
    def has_unmeasured_measurable(self) -> bool:
        return any(f.measurement is None for f in self.measurable)

    # -- wording ----------------------------------------------------------
    def _pairs(self, findings: Sequence[PairFinding], limit: int = 3) -> str:
        names = [self.pair_name(f) for f in findings]
        if len(names) > limit:
            return "; ".join(names[:limit]) + f"; and {len(names) - limit} more"
        return "; ".join(names)

    @property
    def label(self) -> str:
        """One sentence for the subtitle, the footer and the export headers."""
        status = self.status
        if status == STATUS_SINGLE:
            return "list prices; fewer than two policies, so nothing to interact"
        if status == STATUS_NO_OVERLAP:
            return (
                "list prices summed; the selected policies act on separate "
                "parts of the tax code, so no overlap is expected"
            )
        if status == STATUS_STRUCTURALLY_ADDITIVE:
            return (
                "list prices summed; overlapping pairs "
                f"({self._pairs(self.of_kind(KIND_STRUCTURALLY_ADDITIVE))}) "
                "are additive by construction in the calculator, which is a "
                "property of the code and not a measurement"
            )
        parts: list[str] = []
        if status in (STATUS_INTERACTING_UNMEASURED, STATUS_INTERACTING_MEASURED):
            verb = "measured to interact" if status == STATUS_INTERACTING_MEASURED else "overlap and interact"
            parts.append(f"{self._pairs(self.interacting)} {verb}, so their sum is not their joint score")
        unmodelled = self.of_kind(KIND_UNMODELLED)
        if unmodelled:
            overlapping = [f for f in unmodelled if f.shared_channels]
            if overlapping:
                parts.append(
                    f"overlaps not modeled: {self._pairs(overlapping)}"
                )
            elif not parts:
                parts.append("interactions between these policies are not modeled")
        if self.inconsistent:
            parts.append(
                f"list prices not mutually consistent: {self._pairs(self.inconsistent)}"
            )
        if not parts:
            parts.append("interactions between these policies are not modeled")
        return "list prices summed; " + "; ".join(parts)

    @property
    def short_label(self) -> str:
        """The status as a few words, for a badge or a CSV column."""
        return {
            STATUS_SINGLE: "single policy",
            STATUS_NO_OVERLAP: "no overlap expected",
            STATUS_STRUCTURALLY_ADDITIVE: "additive by construction",
            STATUS_INTERACTING_UNMEASURED: "overlaps interact",
            STATUS_INTERACTING_MEASURED: "interaction measured",
            STATUS_ADDITIVE_ONLY_UNMODELLED: "additive only, interactions not modeled",
        }[self.status]


#: Plain-English names for the channels, for sentences a reader sees.
_CHANNEL_LABELS: dict[str, str] = {
    ORDINARY_RATE: "ordinary income tax rates",
    SALT_ITEMIZATION: "itemized deductions",
    STD_DEDUCTION: "the standard deduction",
    AMT_EXEMPTION: "the individual AMT",
    REFUNDABLE_CREDIT: "refundable credits",
    "corporate": "the corporate tax base",
    "international": "international tax",
    "estate": "the estate tax",
    "capital_gains": "capital gains",
    "payroll": "payroll taxes",
    "tariff": "tariffs",
    "health_credit": "ACA premium credits",
    "employer_health": "the employer health exclusion",
    "enforcement": "IRS enforcement",
    "drug_pricing": "drug pricing",
    "climate_credits": "clean-energy credits",
    "carbon_tax": "the carbon tax",
}


def _channel_text(channels: Iterable[str]) -> str:
    return ", ".join(_CHANNEL_LABELS.get(c, c) for c in channels)


def _channels(build_id: str) -> frozenset[str]:
    return INTERACTION_CHANNELS.get(build_id, frozenset({f"unmapped:{build_id}"}))


def _pair_key(a_channels: frozenset[str], b_channels: frozenset[str]) -> str:
    """Relation of two microsim-expressible channel sets: the strongest wins."""
    kinds: set[str] = set()
    for ca in a_channels & MICROSIM_CHANNELS:
        for cb in b_channels & MICROSIM_CHANNELS:
            pair = frozenset({ca, cb})
            if pair in _INTERACTING:
                kinds.add(KIND_INTERACTING)
            elif pair in _STRUCTURALLY_ADDITIVE:
                kinds.add(KIND_STRUCTURALLY_ADDITIVE)
    if KIND_INTERACTING in kinds:
        return KIND_INTERACTING
    if KIND_STRUCTURALLY_ADDITIVE in kinds:
        return KIND_STRUCTURALLY_ADDITIVE
    if a_channels & b_channels & MICROSIM_CHANNELS:
        # The same instrument twice (two SALT reforms): not a pair of
        # policies the calculator can score jointly.
        return KIND_UNMODELLED
    return KIND_NO_OVERLAP


def _display_names(
    selection: Iterable[str], catalog: Mapping[str, Any] | None
) -> dict[str, str]:
    names: dict[str, str] = {}
    if catalog is None:
        return names
    from fiscal_model.ui.tabs.deficit_target import short_name

    for build_id in selection:
        option = catalog.get(build_id)
        if option is not None:
            names[build_id] = short_name(option.label)
    return names


def _groups_of(build_id: str, catalog: Mapping[str, Any] | None) -> tuple[str, ...]:
    option = (catalog or {}).get(build_id)
    if option is not None:
        return tuple(option.exclusive_groups)
    from fiscal_model.preset_ids import exclusive_groups_of

    return tuple(exclusive_groups_of(build_id))


def _subsumes_of(build_id: str, catalog: Mapping[str, Any] | None) -> tuple[str, ...]:
    option = (catalog or {}).get(build_id)
    if option is not None:
        return tuple(option.subsumes)
    from fiscal_model.preset_ids import SUBSUMES

    return tuple(SUBSUMES.get(build_id, ()))


def _inconsistent_findings(
    ordered: Sequence[str],
    catalog: Mapping[str, Any] | None,
    names: Mapping[str, str],
) -> list[PairFinding]:
    """Pairs priced against different baselines for the *same* instrument.

    A bundle (``tcja-full-extension``) subsumes a component
    (``amt-extend-tcja-relief``) and the checklist then refuses the component.
    But a *sibling* of the component -- another member of its exclusive group,
    such as ``amt-repeal-individual`` -- is not subsumed and is accepted, and
    its list price is scored against a different counterfactual for the same
    instrument the bundle has already extended. The two prices are then not
    mutually consistent: ``resolve_selection`` lets them stand together, and a
    sum of them describes no single law. Derived from the catalog's own
    ``subsumes`` and ``exclusive_groups``, never from a hand-kept list.
    """
    out: list[PairFinding] = []
    selected = set(ordered)
    for parent in ordered:
        subsumed = _subsumes_of(parent, catalog)
        for child in subsumed:
            child_groups = set(_groups_of(child, catalog))
            if not child_groups:
                continue
            for other in ordered:
                if other == parent or other in subsumed or other not in selected:
                    continue
                shared = child_groups & set(_groups_of(other, catalog))
                if not shared:
                    continue
                a, b = sorted((parent, other))
                prices = ""
                child_name = _display_names([child], catalog).get(child, child)
                if catalog is not None and child in catalog and other in catalog:
                    prices = (
                        f" (the bundle's own {child_name} is priced "
                        f"{catalog[child].score:+,.0f}B, this one "
                        f"{catalog[other].score:+,.0f}B)"
                    )
                out.append(
                    PairFinding(
                        a=a,
                        b=b,
                        kind=KIND_INCONSISTENT_PRICE,
                        reason=(
                            f"{names.get(parent, parent)} already contains "
                            f"{child_name}, which sits in the same option group "
                            f"as {names.get(other, other)}; "
                            "the two list prices are scored against different "
                            f"baselines for that instrument{prices}, so their sum "
                            "describes no single law"
                        ),
                        shared_channels=tuple(sorted(shared)),
                    )
                )
    return out


def classify_package(
    selection: Iterable[str],
    catalog: Mapping[str, Any] | None = None,
    *,
    measurements: Mapping[tuple[str, str], InteractionMeasurement] | None = None,
) -> PackageInteractionReport:
    """Classify a Build selection. Pure, cheap, order-invariant, deterministic.

    ``catalog`` (``build_id -> BuildOption``) is optional and used only for
    names and for the inconsistent-list-price rule's ``subsumes`` data.
    ``measurements`` carries pairs already measured (the caller keeps them; this
    function never runs the microsim) and turns a pair's ``interacting`` finding
    into a measured one.
    """
    ordered = tuple(sorted(dict.fromkeys(selection)))
    names = _display_names(ordered, catalog)
    measurements = measurements or {}

    if len(ordered) < 2:
        return PackageInteractionReport(
            status=STATUS_SINGLE, selection=ordered, names=names
        )

    findings: list[PairFinding] = []
    for a, b in combinations(ordered, 2):
        ca, cb = _channels(a), _channels(b)
        shared = tuple(sorted((ca & cb) - {"tcja_composite"}))
        both_microsim = a in MICROSIM_MEASURABLE_IDS and b in MICROSIM_MEASURABLE_IDS
        if not both_microsim:
            findings.append(
                PairFinding(
                    a=a,
                    b=b,
                    kind=KIND_UNMODELLED,
                    shared_channels=shared,
                    reason=(
                        f"both act on {_channel_text(shared)}; the repository has "
                        "no joint model for this pair"
                        if shared
                        else "no shared channel identified, but the repository has "
                        "no joint model for this pair"
                    ),
                )
            )
            continue
        kind = _pair_key(ca, cb)
        reason = {
            KIND_INTERACTING: (
                "one changes the base the other's rate or credit is applied to; "
                "scored jointly on the CPS microsim the two do not add"
            ),
            KIND_STRUCTURALLY_ADDITIVE: (
                "the calculator adds one of these after the tax calculation has "
                "run (or computes the two independently), so it cannot see the "
                "other -- additive by construction, not by measurement"
            ),
            KIND_NO_OVERLAP: "they act on different parts of the tax code",
        }[kind]
        findings.append(
            PairFinding(
                a=a,
                b=b,
                kind=kind,
                reason=reason,
                shared_channels=shared,
                measurable=kind == KIND_INTERACTING,
                measurement=measurements.get((a, b)) if kind == KIND_INTERACTING else None,
            )
        )
    findings.extend(_inconsistent_findings(ordered, catalog, names))
    findings.sort(key=lambda f: (f.a, f.b, f.kind))

    kinds = {f.kind for f in findings}
    if KIND_INTERACTING in kinds:
        measured = all(
            f.measurement is not None for f in findings if f.kind == KIND_INTERACTING
        )
        status = STATUS_INTERACTING_MEASURED if measured else STATUS_INTERACTING_UNMEASURED
    elif KIND_UNMODELLED in kinds or KIND_INCONSISTENT_PRICE in kinds:
        status = STATUS_ADDITIVE_ONLY_UNMODELLED
    elif KIND_STRUCTURALLY_ADDITIVE in kinds:
        status = STATUS_STRUCTURALLY_ADDITIVE
    else:
        status = STATUS_NO_OVERLAP

    return PackageInteractionReport(
        status=status, selection=ordered, findings=tuple(findings), names=names
    )


def describe_measurement(report: PackageInteractionReport, finding: PairFinding) -> str:
    """One approximate, plainly-labelled sentence for a measured pair."""
    m = finding.measurement
    if m is None or m.share is None:
        return f"{report.pair_name(finding)}: not measured"
    ref = report.name(m.reference)
    pct = abs(m.share) * 100
    if pct < 0.05:
        effect = "no change from adding the two"
    elif m.share < 0:
        effect = (
            f"revenue comes out lower than the two alone sum to, by about "
            f"{pct:.0f}% of {ref}'s own standalone yield"
        )
    else:
        effect = (
            f"revenue comes out higher than the two alone sum to, by about "
            f"{pct:.0f}% of {ref}'s own standalone yield"
        )
    return (
        f"{report.pair_name(finding)}: scored together, {effect} "
        "(approximate; CPS microsim, a share and not a dollar figure)"
    )
