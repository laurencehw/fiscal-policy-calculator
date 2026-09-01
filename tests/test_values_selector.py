"""
The deterministic half of "Start from your values" (REDESIGN_PLAN.md §5b).

Everything here is a pure function — a vector, a catalog, a package — so it
runs without Streamlit, without an API key, and without the scoring engine
except for the one memoized baseline snapshot the gap arithmetic needs.

The acceptance criteria from plan §5b.8 that live at this layer:

* determinism — the same vector twice yields a byte-identical package;
* the **symmetry harness** — every archetype reaches ≥4 policies and ≥40% of
  its own target, with a why sentence each, so no philosophy can be a strawman
  by construction;
* protected commitments are honoured absolutely;
* nothing outside the catalog is ever emitted;
* ``not_modeled`` and untagged options are treated conservatively.
"""

from __future__ import annotations

import pytest

from fiscal_model.composer.archetypes import (
    ARCHETYPES_PATH,
    archetype_ids,
    get_archetype,
    load_archetypes,
    package_studio_migrations,
    rationale_template_for,
)
from fiscal_model.composer.composer import (
    MAX_VALUES_POLICIES,
    MIN_VALUES_POLICIES,
    CatalogPolicy,
    alignment,
    compose_values_package,
    gap_to_target_billions,
    select_package,
    values_catalog,
)
from fiscal_model.composer.goal_spec import CANNED_GOAL_SPECS
from fiscal_model.composer.values_schema import (
    DIMENSION_BOUNDS,
    PROTECTED_KEYS,
    PROTECTED_RULE_BY_KEY,
    ValuesVector,
    describe,
    from_goal_spec,
    vetoing_rules,
)

#: The plan's own bar, quoted rather than paraphrased.
SYMMETRY_MIN_POLICIES = 4
SYMMETRY_MIN_COVERAGE = 0.40


@pytest.fixture(scope="module")
def catalog():
    return values_catalog()


def _package(archetype_id: str, catalog):
    archetype = get_archetype(archetype_id)
    return compose_values_package(
        archetype.vector, catalog, rationale_template=archetype.rationale_template
    )


# ---------------------------------------------------------------------------
# Values vector schema
# ---------------------------------------------------------------------------


def test_vector_validates_its_own_ranges():
    assert ValuesVector().validate() == []
    problems = ValuesVector(redistribution=2.0, deficit_concern=-1.0).validate()
    assert len(problems) == 2
    assert any("redistribution" in problem for problem in problems)


def test_unknown_protected_key_is_a_validation_problem():
    problems = ValuesVector(protected=("world_peace",)).validate()
    assert problems == ["unknown protected commitment 'world_peace'"]


def test_clamping_is_idempotent_and_orders_protections():
    raw = ValuesVector(
        redistribution=5.0,
        deficit_concern=-3.0,
        protected=("safety_net", "middle_class_rates", "safety_net", "nonsense"),
        target_pct_gdp=99.0,
    )
    once = raw.clamped()
    assert once.redistribution == 1.0
    assert once.deficit_concern == 0.0
    assert once.target_pct_gdp == 6.0
    # Schema order, deduplicated, unknown keys dropped — so the same *set* of
    # protections always serialises to the same string.
    assert once.protected == ("middle_class_rates", "safety_net")
    assert once.clamped() == once
    assert once.validate() == []


def test_vector_round_trips_through_dict_and_base64():
    vector = get_archetype("egalitarian").vector
    assert ValuesVector.from_dict(vector.to_dict()) == vector
    assert ValuesVector.from_base64(vector.to_base64()) == vector


def test_base64_decoding_never_raises_on_junk():
    for token in ("", "!!!", "Zm9v", "eyJhIjoxfQ", None):
        assert ValuesVector.from_base64(token) in (None, ValuesVector.from_dict({}))


def test_goal_spec_adapter_maps_both_ways():
    """``GoalSpec`` survives as a thin adapter, per §5b.1."""
    spec = ValuesVector(redistribution=0.9, deficit_concern=0.9).to_goal_spec()
    assert spec.revenue_philosophy == "progressive"
    assert spec.deficit_stance == "reduce"
    assert spec.validate() == []

    back = from_goal_spec(CANNED_GOAL_SPECS["Deficit hawk"])
    assert back.validate() == []
    assert back.deficit_concern >= 0.8

    investing = from_goal_spec(CANNED_GOAL_SPECS["Progressive investment"])
    assert investing.redistribution > 0.5
    assert investing.govt_size > 0.0


def test_describe_names_every_dimension_and_the_target():
    text = describe(get_archetype("deficit-hawk").vector)
    for label in ("Redistribution", "Deficit concern", "Size of government"):
        assert label in text
    assert "3.0% of GDP" in text
    assert "Protected:" in text


# ---------------------------------------------------------------------------
# Archetypes
# ---------------------------------------------------------------------------


def test_five_archetypes_with_stable_slugs_and_valid_vectors():
    archetypes = load_archetypes()
    assert set(archetypes) == {
        "deficit-hawk",
        "small-government",
        "growth-first",
        "egalitarian",
        "generational-steward",
    }
    for archetype in archetypes.values():
        assert archetype.validate() == []
        assert archetype.one_line
        assert len(archetype.chips) == 3


def test_archetype_names_use_value_language_never_party_language():
    """The plan's naming rule, enforced rather than trusted."""
    banned = (
        "democrat",
        "republican",
        "liberal",
        "conservative",
        "left",
        "right",
        "biden",
        "trump",
        "gop",
        "progressive caucus",
    )
    blob = ARCHETYPES_PATH.read_text(encoding="utf-8").lower()
    # Only the reader-facing strings matter; the file's comments explain the rule.
    for archetype in load_archetypes().values():
        text = f"{archetype.name} {archetype.one_line} {' '.join(archetype.chips)}".lower()
        for word in banned:
            assert word not in text, f"{archetype.id} uses party language: {word!r}"
    assert "never party language" in blob or "never a party" in blob


def test_package_studio_archetypes_were_migrated_not_dropped():
    migrations = package_studio_migrations()
    assert set(migrations) == set(CANNED_GOAL_SPECS)
    assert set(migrations.values()) <= set(archetype_ids())
    assert migrations["Deficit hawk"] == "deficit-hawk"


def test_rationale_template_falls_back_for_an_unknown_archetype():
    assert "{policy}" in rationale_template_for(None)
    assert "{policy}" in rationale_template_for("not-a-philosophy")


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_same_vector_yields_a_byte_identical_package(catalog):
    vector = get_archetype("deficit-hawk").vector
    first = select_package(vector, catalog)
    second = select_package(vector, catalog)
    assert first == second
    assert repr(first) == repr(second)


def test_determinism_survives_a_reordered_catalog(catalog):
    """Selection must not depend on dict iteration order."""
    vector = get_archetype("generational-steward").vector
    shuffled = dict(reversed(list(catalog.items())))
    assert select_package(vector, catalog) == select_package(vector, shuffled)


def test_equivalent_vectors_produce_the_same_package(catalog):
    """Clamping means an out-of-range vector is the same vector."""
    vector = get_archetype("egalitarian").vector
    loose = ValuesVector(
        **{**vector.to_dict(), "protected": list(reversed(vector.protected))}
    )
    assert select_package(vector, catalog) == select_package(loose, catalog)


# ---------------------------------------------------------------------------
# Symmetry harness (§5b.8)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("archetype_id", sorted(archetype_ids()))
def test_symmetry_harness_no_archetype_is_a_strawman(archetype_id, catalog):
    package = _package(archetype_id, catalog)

    assert len(package.picks) >= SYMMETRY_MIN_POLICIES, (
        f"{archetype_id}: only {len(package.picks)} policies"
    )
    assert len(package.picks) <= MAX_VALUES_POLICIES
    assert package.coverage >= SYMMETRY_MIN_COVERAGE, (
        f"{archetype_id}: reaches only {package.coverage:.0%} of its "
        f"{package.vector.target_pct_gdp:.1f}%-of-GDP target"
    )
    for pick in package.picks:
        assert pick.why.strip(), f"{archetype_id}/{pick.policy_id}: no why sentence"
        assert pick.label in pick.why, (
            f"{archetype_id}/{pick.policy_id}: the why does not name the policy"
        )
    assert MIN_VALUES_POLICIES <= len(package.picks)


@pytest.mark.parametrize("archetype_id", sorted(archetype_ids()))
def test_every_archetype_selects_only_catalog_ids(archetype_id, catalog):
    package = _package(archetype_id, catalog)
    assert set(package.policy_ids) <= set(catalog)
    assert len(set(package.policy_ids)) == len(package.policy_ids)


def test_archetypes_produce_visibly_different_packages(catalog):
    """Five philosophies, five readings of the same 47 options."""
    packages = {aid: set(_package(aid, catalog).policy_ids) for aid in archetype_ids()}
    for left in packages:
        for right in packages:
            if left < right:
                assert packages[left] != packages[right], f"{left} == {right}"


# ---------------------------------------------------------------------------
# Protected commitments
# ---------------------------------------------------------------------------


def test_protected_mapping_covers_every_advertised_key():
    assert set(PROTECTED_KEYS) == set(PROTECTED_RULE_BY_KEY)
    for rule in PROTECTED_RULE_BY_KEY.values():
        assert rule.label and rule.clause


@pytest.mark.parametrize(
    ("protected", "must_exclude"),
    [
        ("middle_class_rates", ("tariff-universal-10pct", "carbon-tax-50")),
        ("middle_class_rates", ("cap-employer-health-exclusion",)),
        ("medicare", ("aca-ptc-repeal", "drug-negotiation-expand")),
        ("safety_net", ("aca-ptc-repeal",)),
        ("clean_energy_credits", ("ira-clean-energy-repeal", "ev-credit-repeal")),
        ("corporate_investment", ("corporate-28pct", "international-package")),
    ],
)
def test_a_protection_vetoes_the_policies_it_names(protected, must_exclude, catalog):
    vector = ValuesVector(
        redistribution=0.3,
        deficit_concern=0.9,
        govt_size=0.0,
        growth_priority=0.5,
        generational_weight=0.5,
        protected=(protected,),
        target_pct_gdp=3.0,
    )
    ids = set(compose_values_package(vector, catalog).policy_ids)
    for policy_id in must_exclude:
        assert policy_id in catalog, f"{policy_id} left the catalog; update this test"
        assert policy_id not in ids, f"{protected} failed to veto {policy_id}"


@pytest.mark.parametrize(
    "policy_id", ["tcja-full-extension", "salt-cap-repeal", "estate-repeal"]
)
def test_a_protection_never_vetoes_a_policy_that_helps_the_group(policy_id, catalog):
    """Vetoes are burden-side only: protecting middle-class rates cannot rule
    out a tax cut that *lowers* the burden on them, however regressive it is."""
    tags = catalog[policy_id].tags
    assert tags.get("direction") == "cut_revenue"
    assert vetoing_rules(policy_id, tags, tuple(PROTECTED_KEYS)) == ()


def test_vacuous_protections_are_recorded_honestly(catalog):
    """Nothing in today's catalog cuts SS benefits or defense spending, so both
    commitments currently veto nothing. That is documented in the schema, and
    asserted here so it cannot change silently."""
    for key in ("ss_benefits", "defense"):
        vetoed = [
            policy_id
            for policy_id, policy in catalog.items()
            if vetoing_rules(policy_id, policy.tags, (key,))
        ]
        assert vetoed == [], f"{key} now bites: {vetoed} — update the schema note"


def test_protections_report_what_they_removed(catalog):
    package = _package("egalitarian", catalog)
    vetoed = dict(package.vetoed)
    assert "tariff-universal-10pct" in vetoed
    assert vetoed["tariff-universal-10pct"] == "middle_class_rates"
    # …and the leading pick's sentence names the trade-off out loud.
    assert "rather than" in package.picks[0].why


def test_untagged_options_are_vetoed_whenever_any_commitment_is_named(catalog):
    """We cannot certify an untagged instrument respects a commitment, so it is
    dropped rather than quietly allowed through."""
    untagged = [pid for pid, policy in catalog.items() if not policy.is_tagged]
    assert untagged, "the catalog should still carry score-only options"

    guarded = compose_values_package(
        ValuesVector(deficit_concern=0.9, protected=("defense",)), catalog
    )
    assert not set(guarded.policy_ids) & set(untagged)


# ---------------------------------------------------------------------------
# Overlap structure and the conservative reserve
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("archetype_id", sorted(archetype_ids()))
def test_no_package_double_counts_an_exclusive_group(archetype_id, catalog):
    picks = _package(archetype_id, catalog).policy_ids
    claimed: dict[str, str] = {}
    for policy_id in picks:
        for group in catalog[policy_id].exclusive_groups:
            assert group not in claimed, (
                f"{archetype_id}: {policy_id} and {claimed[group]} both claim {group}"
            )
            claimed[group] = policy_id


@pytest.mark.parametrize("archetype_id", sorted(archetype_ids()))
def test_no_package_pairs_a_bundle_with_its_component(archetype_id, catalog):
    picks = set(_package(archetype_id, catalog).policy_ids)
    for policy_id in picks:
        assert not set(catalog[policy_id].subsumes) & picks, policy_id


def _synthetic_catalog() -> dict[str, CatalogPolicy]:
    """A tiny catalog where the reserve path is reachable in a few picks."""
    tagged = {
        "direction": "raise_revenue",
        "progressivity": "strong_progressive",
        "govt_size": "grow",
        "base": "individual",
        "generational": "current",
    }
    return {
        "big-raiser": CatalogPolicy("big-raiser", "Big Raiser", -1_000.0, "Individual rates", tagged),
        "small-raiser": CatalogPolicy(
            "small-raiser", "Small Raiser", -100.0, "Individual rates", tagged
        ),
        "unmodeled": CatalogPolicy(
            "unmodeled",
            "Unmodeled Saving",
            -5_000.0,
            "Drug pricing",
            {**tagged, "direction": "cut_spending", "progressivity": "not_modeled"},
        ),
        "untagged": CatalogPolicy("untagged", "Untagged Option", -4_000.0, "Other", {}),
    }


def test_not_modeled_options_are_held_back_until_nothing_else_reaches_target():
    catalog = _synthetic_catalog()
    vector = ValuesVector(redistribution=0.8, deficit_concern=0.9, target_pct_gdp=3.0)

    # A target the tagged options cover on their own: the reserve stays shut.
    covered = compose_values_package(vector, catalog, gap_billions=900.0)
    assert set(covered.policy_ids) == {"big-raiser", "small-raiser"}

    # A target they cannot reach: the reserve opens, and says so.
    stretched = compose_values_package(vector, catalog, gap_billions=9_000.0)
    assert "unmodeled" in stretched.policy_ids
    reserve = next(p for p in stretched.picks if p.policy_id == "unmodeled")
    assert reserve.conservative is True
    assert "no distributional tag" in reserve.why


def test_the_reserve_is_ordered_after_every_tagged_option():
    catalog = _synthetic_catalog()
    package = compose_values_package(
        ValuesVector(redistribution=0.8, deficit_concern=0.9),
        catalog,
        gap_billions=9_000.0,
    )
    ids = package.policy_ids
    assert ids.index("big-raiser") < ids.index("unmodeled")
    assert ids.index("small-raiser") < ids.index("unmodeled")


def test_a_commitment_is_priced_against_the_target_not_exempted():
    """A deficit-increasing pick has to be out-raised, not waved through."""
    catalog = _synthetic_catalog()
    catalog["credit"] = CatalogPolicy(
        "credit",
        "A Credit For The Bottom",
        800.0,
        "Tax credits",
        {
            "direction": "add_spending",
            "progressivity": "strong_progressive",
            "govt_size": "grow",
            "base": "transfer",
            "generational": "mixed",
        },
    )
    vector = ValuesVector(
        redistribution=0.9, deficit_concern=0.3, govt_size=0.6, target_pct_gdp=4.5
    )
    package = compose_values_package(vector, catalog, gap_billions=1_000.0)
    commitment = next((p for p in package.picks if p.commitment), None)
    assert commitment is not None and commitment.policy_id == "credit"
    assert package.total_billions == pytest.approx(
        sum(pick.score for pick in package.picks)
    )
    assert package.coverage == pytest.approx(-package.total_billions / 1_000.0)


def test_a_deficit_hawk_never_shops():
    """Above the deficit-concern ceiling, no commitment is taken, however
    well-aligned it is."""
    catalog = _synthetic_catalog()
    catalog["credit"] = CatalogPolicy(
        "credit",
        "A Credit For The Bottom",
        800.0,
        "Tax credits",
        {
            "direction": "add_spending",
            "progressivity": "strong_progressive",
            "govt_size": "grow",
            "base": "transfer",
            "generational": "mixed",
        },
    )
    package = compose_values_package(
        ValuesVector(redistribution=0.9, deficit_concern=0.95, govt_size=0.6),
        catalog,
        gap_billions=1_000.0,
    )
    assert not any(pick.commitment for pick in package.picks)


# ---------------------------------------------------------------------------
# Alignment, why sentences, coverage arithmetic
# ---------------------------------------------------------------------------


def test_alignment_responds_to_the_dimension_it_should(catalog):
    progressive = catalog["ss-cap-eliminate"]
    regressive = catalog["tariff-universal-10pct"]
    egalitarian = ValuesVector(redistribution=1.0, deficit_concern=0.5)
    flat = ValuesVector(redistribution=-1.0, deficit_concern=0.5)

    assert alignment(progressive, egalitarian) > alignment(regressive, egalitarian)
    assert alignment(regressive, flat) > alignment(progressive, flat)


def test_a_pick_the_values_argue_against_says_so(catalog):
    """Small government still has to close the gap, and the sentence admits it."""
    package = _package("small-government", catalog)
    against = [p for p in package.picks if p.alignment < 0]
    assert against, "this archetype should have to reach past its own preferences"
    for pick in against:
        assert "for the arithmetic, not for your values" in pick.why


def test_coverage_matches_the_scoreboard_arithmetic(catalog):
    package = _package("deficit-hawk", catalog)
    assert package.gap_billions == pytest.approx(gap_to_target_billions(3.0))
    assert package.coverage == pytest.approx(
        -package.total_billions / package.gap_billions
    )
    assert package.summary().endswith("% of target")
    assert f"{len(package.picks)} policies" in package.summary()


def test_select_package_is_the_projection_of_compose(catalog):
    vector = get_archetype("growth-first").vector
    template = get_archetype("growth-first").rationale_template
    package = compose_values_package(vector, catalog, rationale_template=template)
    assert select_package(vector, catalog, rationale_template=template) == [
        (pick.policy_id, pick.why) for pick in package.picks
    ]


def test_an_impossible_vector_returns_an_empty_package_rather_than_raising():
    """Every protection at once: nothing is selectable, and nothing explodes."""
    catalog = {
        "only": CatalogPolicy(
            "only",
            "Only Option",
            -1_000.0,
            "Trade / tariffs",
            {
                "direction": "raise_revenue",
                "progressivity": "regressive",
                "govt_size": "grow",
                "base": "consumption",
                "generational": "current",
            },
        )
    }
    package = compose_values_package(
        ValuesVector(protected=tuple(PROTECTED_KEYS)), catalog, gap_billions=1_000.0
    )
    assert package.picks == ()
    assert package.coverage == 0.0
    assert package.summary().startswith("0 policies")


def test_dimension_bounds_and_the_dials_agree():
    """The panel's sliders are built straight off these bounds."""
    assert DIMENSION_BOUNDS["redistribution"] == (-1.0, 1.0)
    assert DIMENSION_BOUNDS["deficit_concern"] == (0.0, 1.0)
    assert set(DIMENSION_BOUNDS) == {
        "redistribution",
        "deficit_concern",
        "govt_size",
        "growth_priority",
        "generational_weight",
    }
