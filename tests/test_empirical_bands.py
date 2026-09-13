"""H4's falsification tests for the Tier 1 accuracy band.

``planning/lanes/HSC_h4_empirical_bands.md`` §4 lists six conditions. The
load-bearing one is **containment**: a class's shipped band must contain that
class's own out-of-sample rows at the coverage the band declares. It is
recomputed here from the live scorecard rather than compared against a constant,
so a hard-coded band, a drifted statistic, or a band built over a different
population all fail rather than pass quietly.
"""

from __future__ import annotations

import pytest

from fiscal_model.validation.credibility import (
    POLICY_TYPE_TO_TIER1_CLASS,
    EmpiricalBand,
    band_for_policy,
    band_for_policy_class,
    band_for_policy_type,
    format_band_caption,
    get_credibility_for_result,
    reset_confidence_cache,
    tier1_class_bands,
)
from fiscal_model.validation.policy_classes import (
    NO_TIER1_CLASS,
    POLICY_CLASS_LABELS,
    classify_policy,
    classify_policy_object,
    no_tier1_class_reason,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_confidence_cache()
    yield
    reset_confidence_cache()


def _tier1_rows() -> dict[str, list[tuple[float, str]]]:
    """The live out-of-sample rows, bucketed by class — the band's own input."""
    from fiscal_model.validation import cached_default_scorecard
    from fiscal_model.validation.scorecard import GENERIC_CATEGORY

    buckets: dict[str, list[tuple[float, str]]] = {}
    for entry in cached_default_scorecard().entries:
        if entry.category != GENERIC_CATEGORY:
            continue
        slug = classify_policy(entry.policy_id)
        buckets.setdefault(slug, []).append(
            (round(entry.abs_percent_difference, 1), entry.policy_id)
        )
    return buckets


# ---------------------------------------------------------------------------
# §4.1 — containment, the condition the plan names
# ---------------------------------------------------------------------------


def test_every_class_band_contains_all_of_its_own_rows_at_the_outer_bound():
    """100% coverage of the outer half-width, recomputed from the scorecard.

    True by construction — the outer half-width *is* the class's worst row — and
    asserted anyway, because "by construction" stops being true the moment
    someone changes which statistic the outer bound reads or which population it
    is computed over. That is precisely the defect H4 replaced: the old band was
    also "by construction" a mean over a category, and the category turned out
    to mix three tiers.
    """
    bands = tier1_class_bands()
    rows = _tier1_rows()
    assert bands, "the scorecard produced no out-of-sample rows at all"

    for slug, band in bands.items():
        errors = [err for err, _ in rows[slug]]
        assert len(errors) == band.n
        outside = [
            policy_id
            for err, policy_id in rows[slug]
            if err > band.max_abs_pct_error
        ]
        assert not outside, (
            f"{slug}: {outside} sit outside their own class's outer band of "
            f"±{band.max_abs_pct_error:.1f}%"
        )


def test_declared_inner_coverage_is_the_measured_inner_coverage():
    """The band says how many of its rows fall inside; the count is checked.

    This is the half that can actually break. The inner half-width is the class
    mean, which is **not** a majority for every class — ``ordinary rate change``
    covers 1 of 4 — so the app may not imply it is one, and the only defence
    against that is asserting the printed count against the distribution.
    """
    bands = tier1_class_bands()
    rows = _tier1_rows()
    for slug, band in bands.items():
        measured = sum(
            1 for err, _ in rows[slug] if err <= band.mean_abs_pct_error
        )
        assert band.rows_inside_mean_band == measured, (
            f"{slug} declares {band.rows_inside_mean_band} of {band.n} inside "
            f"±{band.mean_abs_pct_error:.1f}%, measured {measured}"
        )
        assert 0 <= band.rows_inside_mean_band <= band.n


def test_at_least_one_class_covers_fewer_than_half_its_rows():
    """The honesty check on the check.

    If every class happened to cover a majority, a reader could take the inner
    band for a 50%-plus interval and no test here would catch the drift. One
    class does not, by measurement rather than by design, and this records that
    the copy must never promise coverage it has not computed.
    """
    bands = tier1_class_bands()
    minority = {
        slug: (band.rows_inside_mean_band, band.n)
        for slug, band in bands.items()
        if band.n > 1 and band.rows_inside_mean_band * 2 < band.n
    }
    assert minority, (
        "no class covers fewer than half its rows; if that is now true of the "
        "live battery, delete this test and say so — do not relax the caption"
    )


def test_band_statistics_are_ordered_and_finite():
    for band in tier1_class_bands().values():
        assert band.n >= 1
        assert 0.0 <= band.mean_abs_pct_error <= band.max_abs_pct_error
        assert 0.0 <= band.median_abs_pct_error <= band.max_abs_pct_error
        assert band.worst_policy_id in band.policy_ids
        assert len(band.policy_ids) == band.n


# ---------------------------------------------------------------------------
# §4.2 — the routing is the CI gate's, by import rather than by duplication
# ---------------------------------------------------------------------------


def test_the_gate_and_the_band_share_one_routing_function():
    """``scripts/cold_holdout.py`` must *import* the routing, never fork it."""
    import scripts.cold_holdout as cold_holdout
    from fiscal_model.validation import policy_classes

    assert cold_holdout.classify_policy is policy_classes.classify_policy
    assert cold_holdout.POLICY_CLASS_LABELS is policy_classes.POLICY_CLASS_LABELS
    assert cold_holdout.UNCLASSIFIED_CLASS == policy_classes.UNCLASSIFIED_CLASS


def test_no_tier1_row_is_left_unclassified():
    """An unclassified row would be un-gated *and* silently absent from a band."""
    from fiscal_model.validation.policy_classes import UNCLASSIFIED_CLASS

    stray = [
        policy_id
        for slug, rows in _tier1_rows().items()
        for _, policy_id in rows
        if slug == UNCLASSIFIED_CLASS
    ]
    assert not stray, f"out-of-sample rows in no class: {stray}"


def test_every_band_slug_is_one_of_the_eight_published_classes():
    assert set(tier1_class_bands()) <= set(POLICY_CLASS_LABELS)


# ---------------------------------------------------------------------------
# §4.4 — no band where no row, asserted on the ten modules the route sends
#        nowhere
# ---------------------------------------------------------------------------

_NO_BAND_MODULES = (
    "AMTPolicy",
    "ClimateEnergyPolicy",
    "DrugPricingPolicy",
    "EstateTaxPolicy",
    "IRSEnforcementPolicy",
    "InternationalTaxPolicy",
    "PremiumTaxCreditPolicy",
    "TCJAExtensionPolicy",
    "TariffPolicy",
    "TaxCreditPolicy",
)


@pytest.mark.parametrize("class_name", _NO_BAND_MODULES)
def test_a_module_with_no_tier1_row_gets_no_band_and_a_reason(class_name):
    assert class_name in NO_TIER1_CLASS
    assert NO_TIER1_CLASS[class_name].strip()

    class _Stub:
        pass

    _Stub.__name__ = class_name
    stub = _Stub()
    assert classify_policy_object(stub) is None
    assert band_for_policy(stub) is None
    assert no_tier1_class_reason(stub) == NO_TIER1_CLASS[class_name]


def test_a_policy_type_alone_never_decides_the_class():
    """The four modules whose ``policy_type`` misdescribes what they price.

    ``AMTPolicy`` and ``IRSEnforcementPolicy`` carry ``income_tax`` and
    ``InternationalTaxPolicy`` carries ``corporate_tax``, so a type-only rule
    would hand each of them a band measured on a different reform. Built as real
    objects, not stubs, so the test fails if a module's declared type changes.
    """
    from fiscal_model.amt import create_repeal_individual_amt
    from fiscal_model.enforcement import IRSEnforcementPolicy
    from fiscal_model.international import create_biden_gilti_reform
    from fiscal_model.policies import PolicyType
    from fiscal_model.tcja import create_tcja_extension

    amt = create_repeal_individual_amt()
    assert amt.policy_type.value == "income_tax"
    assert band_for_policy(amt) is None

    gilti = create_biden_gilti_reform()
    assert gilti.policy_type.value == "corporate_tax"
    assert band_for_policy(gilti) is None

    tcja = create_tcja_extension(extend_all=True)
    assert tcja.policy_type.value == "income_tax"
    assert band_for_policy(tcja) is None

    enforcement = IRSEnforcementPolicy(
        name="probe",
        description="probe",
        policy_type=PolicyType.INCOME_TAX,
        annual_enforcement_spending_billions=10.0,
    )
    assert enforcement.policy_type.value == "income_tax"
    assert band_for_policy(enforcement) is None


# ---------------------------------------------------------------------------
# §4.5 — coverage: no Policy subclass may be in neither map
# ---------------------------------------------------------------------------


def test_every_policy_subclass_is_routed_or_explicitly_excluded():
    """PR #119's coverage-grep pattern.

    A module added tomorrow must not silently inherit another class's measured
    accuracy. It is in the route map or in ``NO_TIER1_CLASS`` with a reason, and
    this fails until somebody decides which.
    """
    import importlib

    from fiscal_model.policies_core import Policy, SpendingPolicy, TaxPolicy
    from fiscal_model.validation.policy_classes import _CLASS_ROUTE

    # ``__subclasses__`` only sees classes that have been imported, so every
    # module defining one is loaded first. A module added to the tree and not
    # added here would slip past this test, which is why the list is every
    # module under ``fiscal_model`` that defines a ``Policy`` subclass today.
    for module in (
        "fiscal_model.amt",
        "fiscal_model.climate",
        "fiscal_model.corporate",
        "fiscal_model.credits_core",
        "fiscal_model.enforcement",
        "fiscal_model.estate",
        "fiscal_model.international",
        "fiscal_model.payroll",
        "fiscal_model.pharma",
        "fiscal_model.policies_core",
        "fiscal_model.ptc",
        "fiscal_model.tax_expenditures_core",
        "fiscal_model.tcja",
        "fiscal_model.trade",
    ):
        importlib.import_module(module)

    def _subclasses(cls):
        for sub in cls.__subclasses__():
            yield sub
            yield from _subclasses(sub)

    known = set(_CLASS_ROUTE) | set(NO_TIER1_CLASS) | {
        # Handled by branches rather than by the map, and each has its own test.
        TaxPolicy.__name__,
        SpendingPolicy.__name__,
    }
    missing = sorted(sub.__name__ for sub in _subclasses(Policy) if sub.__name__ not in known)
    assert not missing, (
        f"policy classes in neither _CLASS_ROUTE nor NO_TIER1_CLASS: {missing}. "
        "Decide which Tier 1 class scores it, or record why none does."
    )


def test_the_generic_branch_is_exact_not_isinstance():
    """``type(policy) is TaxPolicy``, because every module subclasses it directly.

    An ``isinstance`` test here would hand ``TariffPolicy`` — a ``TaxPolicy``
    subclass with ``policy_type`` ``excise_tax`` — the ordinary-rate band.
    """
    from fiscal_model.policies import PolicyType, TaxPolicy
    from fiscal_model.trade import TariffPolicy

    generic = TaxPolicy(
        name="probe",
        description="probe",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01,
        affected_income_threshold=0.0,
    )
    assert isinstance(generic, TaxPolicy)
    assert classify_policy_object(generic) == "ordinary_rate_change"

    tariff = TariffPolicy(
        name="probe",
        description="probe",
        policy_type=PolicyType.EXCISE_TAX,
        tariff_rate_change=0.10,
    )
    assert isinstance(tariff, TaxPolicy)
    assert classify_policy_object(tariff) is None


def test_the_income_tax_split_follows_the_base_attribute():
    from fiscal_model.policies import PolicyType, TaxPolicy

    def _policy(**kwargs):
        return TaxPolicy(
            name="probe",
            description="probe",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,
            affected_income_threshold=400_000.0,
            **kwargs,
        )

    assert classify_policy_object(_policy(ordinary_income_base=True)) == "ordinary_rate_change"
    assert classify_policy_object(_policy(ordinary_income_base=False)) == "agi_inclusive_surtax"


def test_a_mandatory_spending_policy_gets_no_discretionary_band():
    """The five spending rows score discretionary budget authority, not transfers.

    ``category`` rather than ``policy_type`` is what a caller sets:
    ``SpendingPolicy.__post_init__`` derives the type from the category and
    overwrites any type passed in, so the two cannot disagree and the routing
    can read either. Written through ``category`` here because that is the
    field a caller who wanted a mandatory policy would reach for.
    """
    from fiscal_model.policies import PolicyType, SpendingPolicy

    discretionary = SpendingPolicy(
        name="probe",
        description="probe",
        policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
        category="nondefense",
        annual_spending_change_billions=10.0,
    )
    assert discretionary.policy_type is PolicyType.DISCRETIONARY_NONDEFENSE
    assert classify_policy_object(discretionary) == "discretionary_spending"

    defense = SpendingPolicy(
        name="probe",
        description="probe",
        policy_type=PolicyType.DISCRETIONARY_DEFENSE,
        category="defense",
        annual_spending_change_billions=10.0,
    )
    assert classify_policy_object(defense) == "discretionary_spending"

    mandatory = SpendingPolicy(
        name="probe",
        description="probe",
        policy_type=PolicyType.MANDATORY_SPENDING,
        category="mandatory",
        annual_spending_change_billions=10.0,
    )
    assert mandatory.policy_type is PolicyType.MANDATORY_SPENDING
    assert classify_policy_object(mandatory) is None
    assert "discretionary" in no_tier1_class_reason(mandatory)


# ---------------------------------------------------------------------------
# The caption and the dollar arithmetic
# ---------------------------------------------------------------------------


def _band(**overrides) -> EmpiricalBand:
    base = dict(
        policy_class="ordinary_rate_change",
        class_label="ordinary rate change",
        n=4,
        mean_abs_pct_error=14.8,
        median_abs_pct_error=16.4,
        max_abs_pct_error=24.5,
        rows_inside_mean_band=1,
        worst_policy_id="illustrative_1pp_all",
        policy_ids=("a", "b", "c", "illustrative_1pp_all"),
    )
    base.update(overrides)
    return EmpiricalBand(**base)


def test_dollar_bands_are_symmetric_in_magnitude_for_either_sign():
    band = _band()
    low, high = band.inner_dollars(-1000.0)
    assert low == pytest.approx(-1148.0)
    assert high == pytest.approx(-852.0)
    low, high = band.inner_dollars(1000.0)
    assert low == pytest.approx(852.0)
    assert high == pytest.approx(1148.0)
    outer_low, outer_high = band.outer_dollars(-1000.0)
    assert outer_low == pytest.approx(-1245.0)
    assert outer_high == pytest.approx(-755.0)


def test_the_caption_names_the_class_the_count_and_the_tier():
    caption = format_band_caption(_band(), point_estimate=-1000.0)
    assert "ordinary rate change" in caption
    assert "4 pre-registered rows" in caption
    assert "14.8%" in caption and "24.5%" in caption
    assert "1 of the 4 falls inside" in caption
    assert "out-of-sample tier only" in caption
    assert "not a confidence interval" in caption
    # Never a single "validated within X%" claim.
    assert "validated within" not in caption.lower()


def test_a_single_row_class_says_n_equals_one_and_does_not_print_two_ranges():
    band = _band(
        policy_class="corporate",
        class_label="corporate",
        n=1,
        mean_abs_pct_error=44.5,
        median_abs_pct_error=44.5,
        max_abs_pct_error=44.5,
        rows_inside_mean_band=1,
        worst_policy_id="cbo_opt64_corporate_rate_1pp",
        policy_ids=("cbo_opt64_corporate_rate_1pp",),
    )
    assert band.is_single_row
    caption = format_band_caption(band, point_estimate=-1397.2)
    assert "n=1" in caption
    assert "one observation, not a distribution" in caption
    assert "at the worst row" not in caption


def test_the_no_band_caption_says_which_tier_is_missing_and_why():
    caption = format_band_caption(None, reason="no pre-registered row scores a tariff")
    assert "No out-of-sample band" in caption
    assert "no pre-registered row scores a tariff" in caption
    assert "44 pre-registered" in caption


# ---------------------------------------------------------------------------
# The result object every surface renders from
# ---------------------------------------------------------------------------


def test_credibility_for_a_generic_run_carries_the_class_band_and_no_row():
    from fiscal_model.policies import PolicyType, TaxPolicy

    policy = TaxPolicy(
        name="1pp, all brackets",
        description="probe",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01,
        affected_income_threshold=0.0,
    )
    credibility = get_credibility_for_result(point_estimate=-1000.0, policy=policy)
    assert credibility is not None
    assert credibility.policy_class == "ordinary_rate_change"
    assert credibility.n_tier1_rows >= 1
    assert credibility.uncertainty_low < -1000.0 < credibility.uncertainty_high
    assert credibility.outer_low <= credibility.uncertainty_low
    assert credibility.outer_high >= credibility.uncertainty_high
    assert credibility.own_row_policy_id is None
    assert credibility.evidence_type == "out_of_sample_class_distribution"


def test_credibility_for_a_fitted_preset_prints_the_row_beside_the_absent_band():
    """TCJA: the most-quoted number in the app, and the tier it sits in.

    The row reproduces its target by construction and the band does not exist,
    and the object has to carry both facts without letting either stand in for
    the other.
    """
    from fiscal_model.tcja import create_tcja_extension

    name = "🏛️ TCJA Full Extension (CBO: $4.6T)"
    credibility = get_credibility_for_result(
        point_estimate=4581.9,
        policy_name=name,
        policy=create_tcja_extension(extend_all=True),
    )
    assert credibility is not None
    assert credibility.policy_class is None
    assert credibility.mean_abs_pct_error is None
    assert credibility.uncertainty_low is None
    assert credibility.evidence_type == "no_out_of_sample_benchmark"
    assert credibility.no_band_reason
    assert credibility.own_row_policy_id == "tcja_full_extension"
    assert credibility.own_row_tier == "fitted"
    assert "construction" in credibility.own_row_caption


def test_no_band_adds_a_limitation_rather_than_saying_nothing():
    from fiscal_model.estate import create_biden_estate_proposal

    credibility = get_credibility_for_result(
        point_estimate=-450.0, policy=create_biden_estate_proposal()
    )
    assert credibility is not None
    assert any("out-of-sample" in item for item in credibility.limitations)


def test_no_policy_and_no_name_returns_none():
    assert get_credibility_for_result(point_estimate=1.0) is None


# ---------------------------------------------------------------------------
# The bill tracker's type-string route
# ---------------------------------------------------------------------------


def test_the_policy_type_route_only_maps_types_with_an_unambiguous_class():
    assert band_for_policy_type("corporate_tax") is not None
    assert band_for_policy_type("payroll_tax") is not None
    assert band_for_policy_type("income_tax") is not None
    # No Tier 1 row scores any of these, so the bill card prints no band.
    for absent in ("estate_tax", "tax_credit", "excise_tax", "medicare", "snap"):
        assert absent not in POLICY_TYPE_TO_TIER1_CLASS
        assert band_for_policy_type(absent) is None
    assert band_for_policy_type(None) is None
    assert band_for_policy_type("not_a_real_type") is None


def test_every_mapped_policy_type_resolves_to_a_real_class():
    for policy_type, slug in POLICY_TYPE_TO_TIER1_CLASS.items():
        assert slug in POLICY_CLASS_LABELS, policy_type
        assert band_for_policy_class(slug) is not None, policy_type


def test_band_lookup_is_cached():
    reset_confidence_cache()
    before = tier1_class_bands.cache_info()
    band_for_policy_class("corporate")
    band_for_policy_class("payroll")
    band_for_policy_class("capital_gains")
    after = tier1_class_bands.cache_info()
    assert after.misses == before.misses + 1
    assert after.hits == before.hits + 2


def test_a_scorecard_failure_yields_no_band_rather_than_an_exception(monkeypatch):
    from fiscal_model.validation import credibility as module

    def _boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "tier1_class_bands", _boom)
    assert band_for_policy_class("corporate") is None
