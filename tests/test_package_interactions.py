"""Package-interaction classification: pure, cheap, and never touches a total.

The Build page quotes official list prices and sums them. These tests pin the
*disclosure* that replaced the blanket "interactions are not modeled" sentence:
which pairs a package holds, how each is classed, and that nothing here can
move ``sum(catalog[bid].score ...)``. The CPS-microsim measurements are in
``test_package_interactions_measured.py``.
"""

from __future__ import annotations

import itertools
import random

import pytest

from fiscal_model import package_interactions as pi
from fiscal_model.package_interactions import (
    INTERACTION_CHANNELS,
    MICROSIM_MEASURABLE_IDS,
    STATUSES,
    classify_package,
)


@pytest.fixture(scope="module")
def catalog():
    from fiscal_model.app_data import CBO_SCORE_MAP
    from fiscal_model.ui.tabs.deficit_target import build_catalog

    return build_catalog(CBO_SCORE_MAP)


# ---------------------------------------------------------------------------
# Coverage (grep style): a new Build option cannot arrive with no channel
# ---------------------------------------------------------------------------


def test_every_catalog_build_id_has_a_channel_entry(catalog):
    missing = sorted(set(catalog) - set(INTERACTION_CHANNELS))
    assert not missing, f"Build options with no interaction channel: {missing}"


def test_no_channel_entry_names_an_unknown_id(catalog):
    from fiscal_model.app_data import PRESETS_BY_ID

    known = set(catalog) | set(PRESETS_BY_ID)
    assert not sorted(set(INTERACTION_CHANNELS) - known)


def test_every_entry_names_at_least_one_channel():
    assert all(channels for channels in INTERACTION_CHANNELS.values())


def test_microsim_measurable_ids_match_what_the_repository_can_express(catalog):
    """The static set is pinned to ``policy_to_microsim_reforms`` itself."""
    expressible = {bid for bid in catalog if pi.microsim_reform(bid)}
    assert expressible == set(MICROSIM_MEASURABLE_IDS)


def test_microsim_reform_is_exactly_the_repositorys_own_function(catalog):
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.composer.composer import _build_preset_policy
    from fiscal_model.distribution_effects import policy_to_microsim_reforms
    from fiscal_model.preset_ids import preset_id_for_token

    label = next(k for k in PRESET_POLICIES if preset_id_for_token(k) == "top-rate-39-6")
    policy, _ = _build_preset_policy(label, PRESET_POLICIES[label])
    assert dict(pi.microsim_reform("top-rate-39-6")) == policy_to_microsim_reforms(policy)


# ---------------------------------------------------------------------------
# Order invariance and determinism
# ---------------------------------------------------------------------------

SAMPLE = [
    "tcja-full-extension",
    "amt-repeal-individual",
    "salt-cap-repeal",
    "top-rate-39-6",
    "corporate-28pct",
]


def test_report_is_order_invariant(catalog):
    reference = classify_package(SAMPLE, catalog)
    rng = random.Random(7)
    for _ in range(25):
        shuffled = SAMPLE[:]
        rng.shuffle(shuffled)
        assert classify_package(shuffled, catalog) == reference


def test_every_permutation_of_a_small_package_agrees(catalog):
    ids = ["top-rate-39-6", "salt-cap-repeal", "eitc-childless-expansion"]
    reports = [classify_package(p, catalog) for p in itertools.permutations(ids)]
    assert all(r == reports[0] for r in reports)


def test_duplicates_do_not_change_the_report(catalog):
    assert classify_package(SAMPLE + SAMPLE, catalog) == classify_package(SAMPLE, catalog)


def test_findings_are_sorted_and_pair_ids_are_canonical(catalog):
    report = classify_package(SAMPLE, catalog)
    assert all(f.a < f.b for f in report.findings)
    keys = [(f.a, f.b, f.kind) for f in report.findings]
    assert keys == sorted(keys)


def test_status_is_always_a_declared_status(catalog):
    for selection in ([], ["ss-donut-250k"], SAMPLE, ["ss-donut-250k", "corporate-28pct"]):
        assert classify_package(selection, catalog).status in STATUSES


def test_an_unmapped_id_degrades_to_unmodelled_rather_than_raising():
    report = classify_package(["top-rate-39-6", "no-such-policy"])
    assert report.status == pi.STATUS_ADDITIVE_ONLY_UNMODELLED


# ---------------------------------------------------------------------------
# Statuses
# ---------------------------------------------------------------------------


def test_zero_and_one_policy_are_single(catalog):
    assert classify_package([], catalog).status == "single"
    assert classify_package(["ss-donut-250k"], catalog).status == "single"


def test_corporate_and_tariff_pairs_are_additive_only(catalog):
    for pair in (
        ["corporate-28pct", "tariff-universal-10pct"],
        ["tariff-china-60pct", "tariff-auto-25pct"],
        ["corporate-28pct", "gilti-reform"],
        ["ss-donut-250k", "corporate-28pct"],
    ):
        report = classify_package(pair, catalog)
        assert report.status == "additive_only_unmodelled", pair
        assert not any(f.measurable for f in report.findings)
        assert pi.measured_interaction_share(*pair) is None


def test_shared_corporate_base_is_named_as_an_overlap_not_modeled(catalog):
    report = classify_package(["corporate-28pct", "gilti-reform"], catalog)
    (finding,) = report.findings
    assert "corporate" in finding.shared_channels
    assert "not modeled" in report.label
    assert report.pair_name(finding) in report.label


def test_rate_and_salt_repeal_are_classed_interacting_and_measurable(catalog):
    report = classify_package(["top-rate-39-6", "salt-cap-repeal"], catalog)
    assert report.status == "interacting_unmeasured"
    (finding,) = report.findings
    assert finding.kind == "interacting" and finding.measurable


@pytest.mark.parametrize(
    "pair",
    [
        ["top-rate-39-6", "eitc-childless-expansion"],  # rate x credits
    ],
)
def test_structurally_additive_pairs_are_labelled_as_a_property_of_the_code(catalog, pair):
    report = classify_package(pair, catalog)
    assert report.status == "structurally_additive"
    # Never "measured zero": a post-hoc adder cannot see the other reform, so a
    # zero from it is not evidence about the provisions.
    assert "by construction" in report.label
    assert "not a measurement" in report.label
    assert "measured" not in report.label.replace("not a measurement", "")


def test_rate_and_amt_exemption_are_structurally_additive_by_channel_rule():
    kind = pi._pair_key(frozenset({pi.ORDINARY_RATE}), frozenset({pi.AMT_EXEMPTION}))
    assert kind == pi.KIND_STRUCTURALLY_ADDITIVE
    kind = pi._pair_key(frozenset({pi.ORDINARY_RATE}), frozenset({pi.REFUNDABLE_CREDIT}))
    assert kind == pi.KIND_STRUCTURALLY_ADDITIVE
    kind = pi._pair_key(frozenset({pi.SALT_ITEMIZATION}), frozenset({pi.AMT_EXEMPTION}))
    assert kind == pi.KIND_INTERACTING


def test_salt_repeal_and_a_childless_eitc_do_not_overlap(catalog):
    report = classify_package(["salt-cap-repeal", "eitc-childless-expansion"], catalog)
    assert report.status == "no_overlap"


# ---------------------------------------------------------------------------
# Inconsistent list prices (the TCJA + AMT-repeal case)
# ---------------------------------------------------------------------------


def test_inconsistent_list_price_flag_fires_for_tcja_plus_amt_repeal(catalog):
    from fiscal_model.ui.tabs.deficit_target import resolve_selection

    # The checklist accepts this package: tcja-full-extension subsumes
    # amt-extend-tcja-relief but not its sibling amt-repeal-individual.
    kept, dropped = resolve_selection(["tcja-full-extension", "amt-repeal-individual"], catalog)
    assert kept == ["tcja-full-extension", "amt-repeal-individual"] and not dropped

    report = classify_package(kept, catalog)
    (flag,) = report.inconsistent
    assert (flag.a, flag.b) == ("amt-repeal-individual", "tcja-full-extension")
    assert "describes no single law" in flag.reason
    assert "+1,357B" in flag.reason and "+450B" in flag.reason
    assert report.status == "additive_only_unmodelled"
    assert "not mutually consistent" in report.label


def test_inconsistent_flag_is_derived_from_the_catalog_not_a_list(catalog):
    # Same rule, different component: TCJA's estate extension vs a sibling.
    report = classify_package(["tcja-full-extension", "estate-exemption-3-5m"], catalog)
    assert len(report.inconsistent) == 1
    # ...and no flag where the sibling is not in the bundle's component's group.
    assert not classify_package(["tcja-full-extension", "corporate-28pct"], catalog).inconsistent


def test_the_flag_also_works_without_a_catalog():
    report = classify_package(["tcja-full-extension", "amt-repeal-individual"])
    assert len(report.inconsistent) == 1


# ---------------------------------------------------------------------------
# HARD CONSTRAINT: the disclosure never edits a total
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "selection",
    [
        ["top-rate-39-6", "salt-cap-repeal"],
        ["ss-donut-250k", "corporate-28pct"],
        ["tcja-full-extension", "amt-repeal-individual", "salt-cap-repeal"],
        SAMPLE,
    ],
)
def test_package_total_is_still_the_plain_sum_of_list_prices(catalog, selection):
    from fiscal_model.app_data import CBO_SCORE_MAP
    from fiscal_model.ui.tabs.deficit_target import package_interaction_report

    scores_before = {bid: opt.score for bid, opt in catalog.items()}
    from_the_map = {
        bid: float(CBO_SCORE_MAP[opt.label]["official_score"]) for bid, opt in catalog.items()
    }
    total_before = sum(catalog[bid].score for bid in selection)

    package_interaction_report(selection, catalog)  # may run the microsim

    assert {bid: opt.score for bid, opt in catalog.items()} == scores_before
    assert sum(catalog[bid].score for bid in selection) == total_before
    assert total_before == sum(from_the_map[bid] for bid in selection)


def test_the_module_never_imports_the_scorer():
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(pi))
    imported = {
        n.module or ""
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom)
    }
    assert not any("scoring" in m or "scorer" in m for m in imported), imported


# ---------------------------------------------------------------------------
# Wording
# ---------------------------------------------------------------------------


def test_the_blanket_sentence_is_gone_from_every_surface():
    from pathlib import Path

    source = Path("fiscal_model/ui/tabs/deficit_target.py").read_text(encoding="utf-8")
    assert "interactions between policies are not" not in source
    assert "list prices, no interaction" not in source
    assert "interaction effects are not modeled" not in source


def test_every_status_has_a_label_and_short_label(catalog):
    cases = {
        "single": [],
        "no_overlap": ["salt-cap-repeal", "eitc-childless-expansion"],
        "structurally_additive": ["top-rate-39-6", "eitc-childless-expansion"],
        "interacting_unmeasured": ["top-rate-39-6", "salt-cap-repeal"],
        "additive_only_unmodelled": ["ss-donut-250k", "corporate-28pct"],
    }
    for status, selection in cases.items():
        report = classify_package(selection, catalog)
        assert report.status == status
        assert report.label.startswith("list prices") and report.short_label
