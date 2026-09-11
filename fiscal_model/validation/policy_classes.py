"""The eight policy classes Tier 1 is reported as, and the two ways in.

``planning/HIGH_STAKES_ACCURACY.md`` §2 reports the out-of-sample tier as eight
populations rather than one, because the pooled mean cannot see a class
regressing while the mean improves -- which is what happened to
``medicare_surcharge_2pp`` in Wave 7 and again to
``warren_ultramillionaire_surtax_3pp`` in Wave B. §3 process rule 4 put a
per-class floor in CI on the strength of it, and Wave C's H4 puts the same
classes behind the accuracy band the app prints.

Two callers, two entry points, **one vocabulary**:

* :func:`classify_policy` takes a **benchmark id** and reads the class off that
  case's own ``CBOScore`` record. It is what ``scripts/cold_holdout.py`` and the
  CI gate use, and it was built by PR #147; this module is where it now lives,
  so the app can import it without importing a script. Its behaviour is
  unchanged, and ``tests/test_cold_holdout.py`` still imports it through the
  script's own namespace.
* :func:`classify_policy_object` takes a **live policy object** -- something a
  user just built on Tailor, in Build, or through the API -- and answers the
  same question about it.

The second is not the first with a different argument, and the difference is the
point.

**Why the object route is an allowlist and not a ``policy_type`` lookup.** Four
modules carry a ``policy_type`` that does not describe the reform they price,
and a type-only rule would hand each of them a band measured on something else:

===========================  ==============  ====================================
Module                       ``policy_type``  What a type-only rule would claim
===========================  ==============  ====================================
``AMTPolicy``                ``income_tax``   the ordinary-rate band, though no
                                              Tier 1 row scores an AMT reform
``InternationalTaxPolicy``   ``corporate_tax`` the corporate band, whose one row
                                              is a *statutory rate* change
``IRSEnforcementPolicy``     ``income_tax``   the ordinary-rate band, though no
                                              Tier 1 row scores an appropriation
``TCJAExtensionPolicy``      ``income_tax``   the ordinary-rate band, for a
                                              bundle of six provisions
===========================  ==============  ====================================

So the route is keyed on the **policy class**, the default is "no class", and
every ``Policy`` subclass in the tree is named either in :data:`_CLASS_ROUTE` or
in :data:`NO_TIER1_CLASS` with a reason. ``tests/test_policy_classes.py`` fails
on a subclass in neither, because "a module nobody swept" is how PR #119's four
offset-sign defects got in.

``type(policy) is TaxPolicy`` in the generic branch is load-bearing: every
module class above subclasses :class:`~fiscal_model.policies_core.TaxPolicy`
*directly*, so an ``isinstance`` test would hand ``TariffPolicy`` the
ordinary-rate band.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "NO_TIER1_CLASS",
    "POLICY_CLASS_LABELS",
    "UNCLASSIFIED_CLASS",
    "classify_policy",
    "classify_policy_object",
    "no_tier1_class_reason",
]


#: Display labels are §2's; the slugs are what the CLI, the workflow and the
#: app's band all speak.
POLICY_CLASS_LABELS: dict[str, str] = {
    "agi_inclusive_surtax": "AGI-inclusive surtax",
    "ordinary_rate_change": "ordinary rate change",
    "capital_gains": "capital gains",
    "corporate": "corporate",
    "enacted_law_spending": "enacted-law spending",
    "discretionary_spending": "discretionary spending",
    "payroll": "payroll",
    "tax_expenditure": "tax expenditure",
}

#: Returned when a benchmark record's shape matches none of the rules below. It
#: is never silently dropped: ``cold_holdout.py --max-class-mean-error`` fails on
#: it, because "a class nobody gated" is how PR #119's four offset-sign defects
#: got in.
UNCLASSIFIED_CLASS = "unclassified"


# ---------------------------------------------------------------------------
# Benchmark ids -- the CI gate's route, moved here unchanged
# ---------------------------------------------------------------------------
#
# Derived from each case's own ``CBOScore`` record, never from a hand-maintained
# list of policy ids, so a row registered tomorrow is classified the moment it is
# registered and cannot quietly escape the gate. The rules reproduce §2's table
# exactly (6 / 4 / 4 / 1 / 3 / 5 / 2 / 1 on the post-Wave-B battery):
#
#   * ``policy_type`` alone settles corporate, payroll, tax-expenditure and
#     capital-gains rows;
#   * an ``income_tax`` row splits on ``agi_inclusive_base`` -- the flag each
#     record already carries, set from how its own source states the base;
#   * a ``spending`` row splits on whether it is one of CBO's own *Options*
#     alternatives (``cbo_options.runnable_score_ids()``, i.e. a budget-authority
#     path CBO published) or a Phase D enacted-law component.


def classify_policy(policy_id: str) -> str:
    """Return the §2 policy-class slug for one out-of-sample ``policy_id``."""
    from fiscal_model.validation.cbo_options import runnable_score_ids
    from fiscal_model.validation.cbo_scores import KNOWN_SCORES

    score = KNOWN_SCORES.get(policy_id)
    if score is None:
        return UNCLASSIFIED_CLASS

    policy_type = getattr(score.policy_type, "value", str(score.policy_type))
    if policy_type == "corporate_tax":
        return "corporate"
    if policy_type == "payroll_tax":
        return "payroll"
    if policy_type == "tax_expenditure":
        return "tax_expenditure"
    if policy_type == "capital_gains_tax":
        return "capital_gains"
    if policy_type == "income_tax":
        if getattr(score, "agi_inclusive_base", False):
            return "agi_inclusive_surtax"
        return "ordinary_rate_change"
    if policy_type == "spending":
        if policy_id in runnable_score_ids():
            return "discretionary_spending"
        return "enacted_law_spending"
    return UNCLASSIFIED_CLASS


# ---------------------------------------------------------------------------
# Live policy objects -- the app's route
# ---------------------------------------------------------------------------

#: Policy class name -> Tier 1 class slug, for the classes one of the 26
#: pre-registered rows actually scores. Keyed by ``__name__`` rather than by the
#: imported class so this module stays off every module's import path; the
#: coverage test resolves the names against the real classes.
_CLASS_ROUTE: dict[str, str] = {
    "CorporateTaxPolicy": "corporate",
    "PayrollTaxPolicy": "payroll",
    "CapitalGainsPolicy": "capital_gains",
    "TaxExpenditurePolicy": "tax_expenditure",
}

#: ``policy_type`` values on a :class:`SpendingPolicy` that the five CBO
#: *Options* budget-authority rows measure. A mandatory or transfer level is a
#: different quantity spent out on a different profile, and no Tier 1 row scores
#: one, so it gets no band rather than the discretionary one.
_DISCRETIONARY_SPENDING_TYPES = frozenset(
    {"discretionary_defense", "discretionary_nondefense"}
)

#: Every other ``Policy`` subclass in the tree, with the reason the battery
#: cannot speak for it. A class in neither this map nor :data:`_CLASS_ROUTE`
#: fails ``tests/test_policy_classes.py``: the point is that adding a module
#: cannot silently inherit somebody else's accuracy.
NO_TIER1_CLASS: dict[str, str] = {
    "AMTPolicy": (
        "no pre-registered row scores an AMT reform; the module's `income_tax` "
        "type would otherwise borrow the ordinary-rate band"
    ),
    "ClimateEnergyPolicy": "no pre-registered row scores a carbon price or an energy credit",
    "DrugPricingPolicy": "no pre-registered row scores a drug-pricing reform",
    "EstateTaxPolicy": "no pre-registered row scores an estate-tax reform",
    "IRSEnforcementPolicy": (
        "no pre-registered row scores an enforcement appropriation; the module's "
        "`income_tax` type would otherwise borrow the ordinary-rate band"
    ),
    "InternationalTaxPolicy": (
        "the one pre-registered corporate row is a statutory rate change, not a "
        "GILTI, FDII or Pillar Two reform"
    ),
    "PremiumTaxCreditPolicy": "no pre-registered row scores a premium-tax-credit reform",
    "TCJAExtensionPolicy": (
        "no pre-registered row scores a bundle of rates, brackets, the standard "
        "deduction, the CTC, the AMT and QBI together"
    ),
    "TariffPolicy": "no pre-registered row scores a tariff",
    "TaxCreditPolicy": "no pre-registered row scores a refundable credit",
    "TransferPolicy": "no pre-registered row scores a transfer-payment change",
}


def _spending_class(policy: Any) -> str | None:
    raw = getattr(getattr(policy, "policy_type", None), "value", None)
    if raw in _DISCRETIONARY_SPENDING_TYPES:
        return "discretionary_spending"
    return None


def classify_policy_object(policy: Any) -> str | None:
    """Return the Tier 1 class slug a live policy belongs to, or ``None``.

    ``None`` means the pre-registered battery contains no row scoring a policy
    of this kind — which is the answer for two thirds of the shipped catalog and
    is a measurement, not a gap to be papered over.
    """
    if policy is None:
        return None

    # Imported here rather than at module scope: this module is read by the app's
    # result surfaces and by a CI script, and neither should drag in the policy
    # package to ask a routing question about a class it may not be holding.
    from fiscal_model.policies_core import SpendingPolicy, TaxPolicy

    name = type(policy).__name__
    routed = _CLASS_ROUTE.get(name)
    if routed is not None:
        return routed
    if name in NO_TIER1_CLASS:
        return None

    if isinstance(policy, SpendingPolicy):
        return _spending_class(policy)

    # The generic path, and only the generic path. Every module class above
    # subclasses TaxPolicy directly, so `isinstance` here would hand TariffPolicy
    # the ordinary-rate band.
    if type(policy) is TaxPolicy:
        raw = getattr(getattr(policy, "policy_type", None), "value", None)
        if raw != "income_tax":
            return None
        if getattr(policy, "ordinary_income_base", True):
            return "ordinary_rate_change"
        return "agi_inclusive_surtax"

    return None


def no_tier1_class_reason(policy: Any) -> str:
    """Why :func:`classify_policy_object` returned ``None``, in one clause."""
    if policy is None:
        return "no policy was scored"
    name = type(policy).__name__
    recorded = NO_TIER1_CLASS.get(name)
    if recorded:
        return recorded

    from fiscal_model.policies_core import SpendingPolicy, TaxPolicy

    if isinstance(policy, SpendingPolicy):
        return (
            "the five pre-registered spending rows score discretionary "
            "budget-authority paths; this policy is not one"
        )
    if type(policy) is TaxPolicy:
        return (
            "the pre-registered income-tax rows score rate changes on the "
            "ordinary or AGI-inclusive base; this policy is neither"
        )
    return f"no pre-registered row scores a {name}"
