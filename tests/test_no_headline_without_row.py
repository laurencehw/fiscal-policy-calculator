"""No headline without a row — lane H6 of ``planning/HIGH_STAKES_ACCURACY.md``.

Three rules, enforced here rather than by review:

1. every preset carrying a ``CBO_SCORE_MAP`` ``official_score`` has a badge, and
   the badge names the tier its row sits in;
2. a preset with **no** scorecard row of any tier may not print a dollar figure
   in its label;
3. the confidence headline is keyed to the tier, not to ``CBO_SCORE_MAP``
   membership — the defect that gave a fitted 0.0% and a 701% reconstruction the
   same "High confidence" badge (plan §1.3(d)).

Rule 2 fails on this lane's own branch by exactly four presets. The label edits
ship in H1's PR, because both lanes would otherwise edit ``app_data.py`` and
Wave A is file-disjoint (plan §4, "Conflict notes"); H6 owns the rule.
"""

from __future__ import annotations

import re

import pytest

from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.preset_ids import (
    CATALOG_PRESET_IDS,
    label_for_preset_id,
    preset_id_for_label,
)
from fiscal_model.ui.preset_validation import (
    HEADLINE_ROW_DIVERGENCE,
    HEADLINE_ROW_TOLERANCE_PCT,
    PRESET_ID_TO_SCORECARD_ID,
    TIER_LABELS,
    TIER_NOTES,
    badge_tier,
    get_validation_badge,
    presets_without_a_row,
    reset_scorecard_cache,
)

#: A *score* figure in a label: a parenthesised dollar amount, optionally
#: prefixed by an estimator ("(CBO: $4.6T)", "(-$450B)", "($400B)"). A dollar
#: amount that is a policy *parameter* — "SS Donut Hole $250K", "Carbon Tax
#: \\$25/ton" — is not one, which is why the pattern is anchored on the bracket.
_SCORE_FIGURE_RE = re.compile(
    r"\(\s*(?:[A-Za-z][A-Za-z/. ]*:\s*)?[-−+]?\s*\\?\$\s*[\d,.]+\s*[TBM]?\b"
)


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_scorecard_cache()
    yield
    reset_scorecard_cache()


def _catalog_ids() -> tuple[str, ...]:
    return CATALOG_PRESET_IDS


def _presets_with_an_official_score() -> set[str]:
    ids = set()
    for label, entry in CBO_SCORE_MAP.items():
        if label not in PRESET_POLICIES:
            continue  # a score-only Build option, with no preset to badge
        if entry.get("official_score") is None:
            continue
        ids.add(preset_id_for_label(label))
    return ids


# ---------------------------------------------------------------------------
# Rule 1 — every official figure has a row behind it, and the badge says which
# ---------------------------------------------------------------------------


def test_every_preset_with_an_official_score_has_a_badge():
    """The rule, in the direction that matters: a figure on screen with nothing
    checking it."""
    missing = sorted(_presets_with_an_official_score() - set(PRESET_ID_TO_SCORECARD_ID))
    assert not missing, (
        "these presets print a CBO_SCORE_MAP official_score with no scorecard "
        f"row behind it: {missing}"
    )


def test_no_badge_without_an_official_score():
    """And the other direction, so the map cannot drift into a wishlist."""
    extra = sorted(set(PRESET_ID_TO_SCORECARD_ID) - _presets_with_an_official_score())
    assert not extra, (
        f"badged presets with no CBO_SCORE_MAP official_score: {extra}"
    )


def test_the_two_sets_are_the_same_42_presets():
    """Pinned as a count as well as a set, so a preset added without either half
    is a failure rather than a silent shrink on both sides.

    44 until lane R2, which retired the Warren surtax's and the Medicare
    surcharge's Tier 1 rows for want of a published target and removed both
    ``CBO_SCORE_MAP`` official scores with them. Both presets still ship and
    still score; they show the model's own estimate with no official
    comparison, which is the normal case for most of the catalog. The catalog
    count is unchanged at 52, which is the point of pinning all three: the
    presets did not go anywhere, only the claims about them did.
    """
    assert len(_presets_with_an_official_score()) == 42
    assert len(PRESET_ID_TO_SCORECARD_ID) == 42
    assert len(_catalog_ids()) == 52


def test_every_badge_names_its_tier():
    for preset_id in PRESET_ID_TO_SCORECARD_ID:
        badge = get_validation_badge(preset_id)
        assert badge is not None, preset_id
        assert badge["tier"] in {"fitted", "reconstruction", "out_of_sample"}, preset_id
        assert badge["tier_label"] == TIER_LABELS[badge["tier"]]
        assert badge["tier_note"] == TIER_NOTES[badge["tier"]]
        assert badge["caption"], preset_id


def test_the_tier_composition_is_what_the_lane_registered():
    """15 fitted / 26 unfitted reconstructions / 3 out-of-sample. If this moves,
    a benchmark changed tier and the docs quoting it are stale.

    H6 registered 20 / 21 / 3; H9's provenance pass then moved five fitted
    targets onto their documents (``ss_donut_250k``, ``tcja_rates_only``,
    ``eliminate_estate_tax``, ``repeal_ira_credits``, ``eliminate_mortgage``),
    so a constant fitted to the superseded figure reports as a reconstruction.
    H7 then moved a sixth on PR #119's *other* rule: ``cap_charitable``'s
    annual reproduced -$200.0B only through an unsourced 0.40 behavioural
    magnitude, and a constant fitted through an unsourced magnitude the lane
    then sourced is not a calibration to that target either.

    Lane R2 then took out-of-sample 3 -> 1 by retiring two of the three badged
    Tier 1 rows (the Warren surtax and the Medicare surcharge, neither target
    traceable to any publication). The survivor is ``biden_high_income_tax``,
    whose target is a printed Green Book row. **A single out-of-sample badge is
    thin** and the count is pinned here so that reads as a finding rather than
    as a coincidence: R3 is the lane that widens the battery and should widen
    this alongside it.
    """
    counts: dict[str, int] = {}
    for preset_id in PRESET_ID_TO_SCORECARD_ID:
        tier = get_validation_badge(preset_id)["tier"]
        counts[tier] = counts.get(tier, 0) + 1
    assert counts == {"fitted": 15, "reconstruction": 26, "out_of_sample": 1}


def test_the_three_tiers_are_never_collapsed_into_one_claim():
    """CLAUDE.md: never one "validated within X%" number across the tiers."""
    assert len({TIER_LABELS[t] for t in TIER_LABELS}) == len(TIER_LABELS)
    assert len({TIER_NOTES[t] for t in TIER_NOTES}) == len(TIER_NOTES)
    for preset_id in PRESET_ID_TO_SCORECARD_ID:
        caption = get_validation_badge(preset_id)["caption"].lower()
        assert "validated within" not in caption, preset_id
        if badge_tier(preset_id) == "fitted":
            # A fitted row's rating is arithmetic; it may not be sold as a test.
            assert "excellent" not in caption, preset_id
            assert "independent" in caption, preset_id


# ---------------------------------------------------------------------------
# Rule 2 — no dollar figure in the label of a preset with no row
# ---------------------------------------------------------------------------


def test_a_preset_with_no_row_may_not_print_a_dollar_figure():
    """Expected to fail on this branch by exactly four presets, and to pass once
    H1 strikes those figures (plan §1.4, §3 H6 rule 2)."""
    offenders = []
    for preset_id in presets_without_a_row():
        label = label_for_preset_id(preset_id)
        match = _SCORE_FIGURE_RE.search(label)
        if match:
            offenders.append((preset_id, match.group(0)))
    assert not offenders, (
        "these presets have no scorecard row of any tier and still print a "
        f"dollar figure in their label: {offenders}"
    )


def test_the_no_row_set_is_the_ten_the_lanes_enumerated():
    """Eight after H6; ten after lane R2 retired two Tier 1 rows whose targets
    are in no publication. Both new members keep their preset and lose only the
    comparison, and neither prints a dollar figure in its label, which is what
    the rule above actually forbids."""
    assert set(presets_without_a_row()) == {
        "millionaire-surtax-5pp",
        "middle-class-rate-cut-2pp",
        "across-the-board-rate-cut-5pp",
        "top-rate-45",
        "irs-enforcement-high-income",
        "drug-reform-comprehensive",
        "carbon-tax-25",
        "ira-clean-energy-extend",
        # Lane R2: TPC prices no 3pp AGI surtax and Treasury's surcharge is
        # 1.2pp, so neither carried a traceable official score.
        "ultra-millionaire-surtax-3pp",
        "medicare-surcharge-2pp",
    }


def test_the_score_figure_pattern_reads_a_score_and_not_a_parameter():
    """The rule bans a *score* in a label, not a dollar amount: "SS Donut Hole
    $250K" is the policy's own threshold and must survive."""
    assert _SCORE_FIGURE_RE.search("💰 SS Donut Hole $250K") is None
    assert _SCORE_FIGURE_RE.search("🌱 Carbon Tax \\$25/ton") is None
    assert _SCORE_FIGURE_RE.search("Top Rate to 45%") is None
    assert _SCORE_FIGURE_RE.search("🏛️ TCJA Full Extension (CBO: $4.6T)")
    assert _SCORE_FIGURE_RE.search("🏠 Biden Estate Reform (-$450B)")
    assert _SCORE_FIGURE_RE.search("🌱 Extend IRA Credits Beyond 2032 ($400B)")


# ---------------------------------------------------------------------------
# The badge has to be about the number on the screen
# ---------------------------------------------------------------------------


def test_the_row_behind_a_badge_scores_the_headline():
    """A badge asserts something about the figure the app prints, so the row
    behind it has to score the object the preset builds.

    40 of the 44 agree to 0.0%. The four that do not are declared in
    ``HEADLINE_ROW_DIVERGENCE`` with their cause; an undeclared one fails here.
    """
    from fiscal_model.composer.composer import _build_preset_policy, _scorer_for

    undeclared: list[tuple[str, float]] = []
    measured: dict[str, float] = {}
    for preset_id in PRESET_ID_TO_SCORECARD_ID:
        label = label_for_preset_id(preset_id)
        policy, use_real_data = _build_preset_policy(label, PRESET_POLICIES[label])
        result = _scorer_for(policy, use_real_data).score_policy(policy, dynamic=False)
        app_total = sum(float(v) for v in result.final_deficit_effect)
        row_total = get_validation_badge(preset_id)["model"]
        gap = abs(app_total - row_total) / abs(row_total) * 100.0 if row_total else 0.0
        measured[preset_id] = gap
        if gap > HEADLINE_ROW_TOLERANCE_PCT and preset_id not in HEADLINE_ROW_DIVERGENCE:
            undeclared.append((preset_id, round(gap, 1)))

    assert not undeclared, (
        "the scorecard row behind these badges does not score the number the "
        f"app prints, and the divergence is not declared: {undeclared}"
    )

    # The structural divergences are permanent until the validation window or a
    # runner moves, so the registry cannot rot into a blanket exemption. The
    # ``base_rule`` entries are deliberately not asserted: they close when H1
    # lands its shared base default, and the entry should be deleted then.
    for preset_id, (kind, _note) in HEADLINE_ROW_DIVERGENCE.items():
        assert preset_id in PRESET_ID_TO_SCORECARD_ID, preset_id
        assert kind in {"base_rule", "runner_shape", "baseline"}, preset_id
        if kind in {"runner_shape", "baseline"}:
            assert measured[preset_id] > HEADLINE_ROW_TOLERANCE_PCT, (
                f"{preset_id} no longer diverges — delete its "
                "HEADLINE_ROW_DIVERGENCE entry"
            )


# ---------------------------------------------------------------------------
# Rule 3 — the confidence headline is keyed to the tier
# ---------------------------------------------------------------------------


class _Policy:
    taxable_income_elasticity = 0.25

    def __init__(self, name: str) -> None:
        self.name = name


class _Result:
    is_dynamic = False
    # The old implementation preferred this field over everything else, which is
    # how a fitted 0.0% became "High confidence".
    error_pct = 0.0


def _context(preset_id: str) -> str:
    from fiscal_model.ui.controller_utils import get_confidence_context

    return get_confidence_context(None, _Policy(label_for_preset_id(preset_id)), _Result())


def test_confidence_is_keyed_to_the_tier_not_to_score_map_membership():
    fitted = _context("ss-cap-eliminate")
    reconstruction = _context("drug-reference-pricing")
    # Lane R2 retired medicare-surcharge-2pp's row, so the out-of-sample
    # exemplar is now the one Tier 1 preset whose target is a printed document
    # row -- Treasury's FY2025 Green Book line for the 39.6% top rate.
    out_of_sample = _context("top-rate-39-6")
    no_row = _context("across-the-board-rate-cut-5pp")
    # Fitted when H6 wrote this test; H9 moved its target onto CBO Option 62
    # alternative 2, so the same preset now reads as a reconstruction 89% off.
    revised_out = _context("ss-donut-250k")

    assert "Calibrated" in fitted
    assert "by construction" in fitted
    assert "Unfitted reconstruction" in reconstruction
    assert "701.0%" in reconstruction
    assert "Unfitted reconstruction" in revised_out
    assert "89.2%" in revised_out
    assert "Out-of-sample prediction" in out_of_sample
    assert "Exploratory" in no_row

    # All four are distinct headlines, and none of them is the old one.
    headlines = {
        text.split("\n")[1] for text in (fitted, reconstruction, out_of_sample, no_row)
    }
    assert len(headlines) == 4
    for text in (fitted, reconstruction, out_of_sample, no_row):
        assert "High confidence" not in text


def test_confidence_no_longer_quotes_a_single_out_of_sample_number():
    """The old text promised "mean out-of-sample error on such policies is ~8%".
    The tier is eight populations with a tight core and a long tail, not one
    number."""
    for preset_id in ("ss-donut-250k", "across-the-board-rate-cut-5pp"):
        assert "~8%" not in _context(preset_id)
        assert "\\~8%" not in _context(preset_id)


def _validation_line(preset_id: str) -> str:
    for line in _context(preset_id).splitlines():
        if line.startswith("- **Validation:**"):
            return line
    raise AssertionError(f"no validation line for {preset_id}")


def test_the_unvalidated_fallback_carries_no_hard_coded_error_figure():
    """It used to read "spans 1.5% to 49.8% across 26 cases" — three numbers
    that go stale the moment the battery moves, and two of them the kind of
    collapsed claim the tiers exist to prevent. A percentage here is the defect,
    whatever its value."""
    line = _validation_line("across-the-board-rate-cut-5pp")
    assert not re.search(r"\d+(\.\d+)?\s*%", line), line
    assert "1.5%" not in line and "49.8%" not in line


def test_the_fallback_tier_size_is_derived_and_not_typed():
    """The one number it does carry is the tier's *size*, read from the
    generated artifact, so a lane that registers a case moves this text too."""
    from fiscal_model.ui.validation_headline import pinned_out_of_sample_entries

    count = pinned_out_of_sample_entries()
    assert isinstance(count, int) and count > 0
    assert f"({count} cases)" in _validation_line("across-the-board-rate-cut-5pp")


def test_the_pinned_tier_size_is_the_scorecard_tier_size():
    """And the artifact is not typed either: it is the count of ``Generic``
    scorecard rows, which is what ``cold_holdout.py`` reports as Tier 1."""
    from fiscal_model.ui.validation_headline import (
        GENERIC_CATEGORY,
        pinned_out_of_sample_entries,
    )
    from fiscal_model.validation import cached_default_scorecard

    live = sum(
        1
        for e in cached_default_scorecard().entries
        if e.category == GENERIC_CATEGORY
    )
    assert pinned_out_of_sample_entries() == live


def test_the_fallback_survives_a_missing_artifact(monkeypatch):
    """A missing count drops the parenthetical rather than printing "(0 cases)"
    or raising: the sentence has to stay true when the file cannot be read."""
    from fiscal_model.ui import validation_headline as vh

    monkeypatch.setattr(vh, "pinned_out_of_sample_entries", lambda: None)
    line = _validation_line("across-the-board-rate-cut-5pp")
    assert "cases)" not in line
    assert "out-of-sample tier" in line


def test_confidence_survives_an_unknown_policy_name():
    from fiscal_model.ui.controller_utils import get_confidence_context

    text = get_confidence_context(None, _Policy("Some custom thing"), _Result())
    assert "Exploratory" in text
    assert "Elasticity (ETI)" in text
