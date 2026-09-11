"""The two category maps that survived H4, and what they are now for.

``PRESET_AREA_TO_SCORECARD_CATEGORY`` and ``POLICY_TYPE_TO_SCORECARD_CATEGORY``
used to carry an **accuracy claim**: a mean over ``summary.by_category`` that
blended fitted bookkeeping with unfitted reconstructions and fell back to the
whole Tier 1 tier for every unmapped area. Wave C's H4 moved the accuracy claim
onto the eight out-of-sample policy classes — see
``tests/test_empirical_bands.py`` — and left these two maps routing the things
that really are per-category facts: the **known-limitations** list and the
**holdout-availability** label.

Both still have to be total, for the same reason as before: a category with no
mapping silently becomes ``Generic``, and a ``Generic`` fallback is what let a
701%-from-target pharma preset print the Tier 1 tier's own mean.
"""

from __future__ import annotations

from fiscal_model.ui.confidence_band import (
    POLICY_TYPE_TO_SCORECARD_CATEGORY,
    PRESET_AREA_TO_SCORECARD_CATEGORY,
)
from fiscal_model.validation.credibility import category_for_result


def test_mapping_dicts_cover_every_preset_area():
    """Every UI category produced by _preset_category should map somewhere."""
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.ui.policy_input_presets import _preset_category

    seen_areas = {_preset_category(p) for p in PRESET_POLICIES.values()}
    missing = seen_areas - PRESET_AREA_TO_SCORECARD_CATEGORY.keys()
    assert not missing, f"preset areas missing from category map: {missing}"


def test_mapping_dicts_cover_every_policy_type_value():
    """Every PolicyType enum value must have a category mapping."""
    from fiscal_model.policies import PolicyType

    enum_values = {p.value for p in PolicyType}
    missing = enum_values - POLICY_TYPE_TO_SCORECARD_CATEGORY.keys()
    assert not missing, f"PolicyType values missing from map: {missing}"


def test_category_prefers_the_preset_area_over_the_policy_type():
    """A ``TCJAExtensionPolicy`` says ``income_tax``; its limitations are TCJA's."""
    from types import SimpleNamespace

    policy = SimpleNamespace(policy_type=SimpleNamespace(value="income_tax"))
    assert (
        category_for_result(
            policy_name="🏛️ TCJA Full Extension (CBO: $4.6T)", policy=policy
        )
        == "TCJA"
    )


def test_category_falls_back_to_the_policy_type_then_to_generic():
    from types import SimpleNamespace

    policy = SimpleNamespace(policy_type=SimpleNamespace(value="corporate_tax"))
    assert category_for_result(policy_name="One-off custom hike", policy=policy) == "Corporate"
    assert category_for_result(policy_name=None, policy=None) == "Generic"


def test_the_category_maps_no_longer_export_an_accuracy_object():
    """The replaced names are gone rather than aliased, and deliberately.

    A stale caller reading ``mean_abs_pct_error`` off a differently-populated
    object would print a wrong number in silence; an ``ImportError`` is the
    louder failure. ``fiscal_model/ui/confidence_band.py`` says so in its own
    docstring, and this asserts it.
    """
    import fiscal_model.ui.confidence_band as shim
    import fiscal_model.validation.credibility as credibility

    for gone in (
        "ConfidenceBand",
        "estimate_uncertainty_dollars",
        "get_band_for_policy_type",
        "get_band_for_preset_area",
        "get_band_for_result",
    ):
        assert not hasattr(shim, gone), gone
        assert not hasattr(credibility, gone), gone
