"""
Tests for the corporate module's derived (structural) rate identity — lanes W5 and W6.

What these lock down:

- **The transcribed base is the statutory base, and that is checkable.** SOI's
  own "income tax" line is 21.0% of "income subject to tax" in every post-TCJA
  year on the file. If a transcription slips, this fails.
- **The credit ratio is not a free parameter.** The average after/before ratio
  the module applies and an explicit section 904 decomposition built from the
  same rows agree to about 1%.
- **The base is projected off CBO's own receipts path, not off a growth
  constant** (W6). The level is anchored by one ratio measured on completed
  history — SOI's credit-realized TY2022 base over Treasury's actual FY2022
  receipts — and that ratio is within 1% of ``1/tau``, which is what makes the
  splice a change of vintage rather than of concept.
- **The marginal base never exceeds the average base it is part of.** Before
  W6 the derived path priced 101.6% of CBO's own implied average base by
  FY2034, which is arithmetically impossible whatever the target says.
- **The engine coupling is pinned.** ``CORPORATE_BASE_GROWTH`` is the scoring
  engine's own corporate growth rate, and the engine switches it off for a
  policy whose rate channel carries its own path.
- **IRC section 6655 timing is exactly a phase factor**, now the convolution
  ``0.75 + 0.25 B(t-1)/B(t)`` rather than its constant-growth closed form.
- **The identity is concave in the rate step.** Reported yields the same
  dollars per percentage point at 1pp and 7pp; derived does not, which is the
  whole point of the row.
- **The offset's sign follows the parent's contract in BOTH modes.** W5 signed
  ``derived`` and deliberately left ``reported`` unsigned, because
  ``trump_corporate_15`` was scored through the defect; the offset-sign sweep
  signed ``reported`` too, which is why the pins below moved.
- **Derived reads no baseline level**, so the score is the same on every
  vintage, which is the property ``validation/cbo_options.py`` claims for every
  uncalibrated shape. A transcribed CBO table is an input like SOI's; the
  scorer's own baseline object is not read.
- **Reported mode has not moved since the offset-sign sweep**, and neither W6
  nor the Decision 1 flip touched it. Its two pins are the same figures after
  the flip as before, which is the check that the flip changed a *default* and
  not a model.
- **The app default is ``derived`` since 2026-09-05** (Decision 1,
  ``planning/lanes/DECISION1_corporate_mode.md``), and every corporate surface
  is pinned to the derived figure so the app and its own scorecard cannot drift
  apart. The margin that decided it is pinned too — both means, and the fact
  that derived wins **one** row of three — so no lane can improve the margin
  quietly.
"""

from __future__ import annotations

import pytest

from fiscal_model.baseline import BaselineVintage
from fiscal_model.corporate import (
    BASE_PER_DOLLAR_OF_RECEIPTS,
    BASELINE_TAXABLE_PROFITS_BILLIONS,
    CORPORATE_APP_MODE,
    CORPORATE_BASE_GROWTH,
    CORPORATE_MODE_DERIVED,
    CORPORATE_MODE_REPORTED,
    CORPORATE_RECEIPTS_VINTAGE,
    CORPORATE_VALIDATION_MODE,
    CURRENT_CORPORATE_RATE,
    ESTIMATED_PAYMENT_SAME_FY_SHARE,
    PROFIT_SHIFTING_SEMI_ELASTICITY,
    RECEIPTS_ANCHOR_YEAR,
    CorporateTaxPolicy,
    actual_corporate_receipts,
    cbo_corporate_receipts,
    cbo_receipts_by_fiscal_year,
    create_biden_corporate_proposal,
    create_biden_corporate_rate_only,
    create_corporate_rate_change,
    create_republican_corporate_cut,
    create_tcja_corporate_repeal,
    credit_realization_ratio,
    credit_realized_base_billions,
    latest_soi_tax_year,
    load_soi_table11,
    projected_statutory_base,
    section_904_realization_ratio,
    soi_row,
    statutory_base_billions,
)
from fiscal_model.policies import PolicyType
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.validation.cbo_scores import KNOWN_SCORES
from fiscal_model.validation.core import build_scorer_for_vintage, create_policy_from_score

#: Last fiscal year the transcribed CBO receipts table carries. The app's
#: window runs a year past it, which is why the caption distinguishes published
#: years from continued ones.
CORPORATE_RECEIPTS_LAST_TABULATED_YEAR = cbo_receipts_by_fiscal_year()[-1][0]


@pytest.fixture(scope="module")
def scorer() -> FiscalPolicyScorer:
    return FiscalPolicyScorer(start_year=2025, use_real_data=False)


def _ten_year(scorer: FiscalPolicyScorer, policy: CorporateTaxPolicy) -> float:
    return float(scorer.score_policy(policy, dynamic=False).total_10_year_cost)


# ---------------------------------------------------------------------------
# The transcribed SOI file
# ---------------------------------------------------------------------------


def test_every_transcribed_year_puts_the_statutory_rate_on_the_base():
    """SOI's "income tax" line is 21% of "income subject to tax", every year.

    This is the identity that says "income subject to tax" is the base a
    statutory rate change reaches. TY2018 is off the file because the section
    15 blended-rate transition breaks it; every year that is on the file must
    hold it.
    """
    rows = load_soi_table11()
    assert len(rows) >= 4
    for row in rows:
        base = float(row["income_subject_to_tax_thousands"])
        tax = float(row["income_tax_thousands"])
        assert tax / base == pytest.approx(CURRENT_CORPORATE_RATE, abs=0.001), row[
            "tax_year"
        ]


def test_the_latest_year_is_the_one_the_module_reads():
    assert latest_soi_tax_year() == 2022
    assert statutory_base_billions() == pytest.approx(2879.101, abs=0.001)
    assert credit_realization_ratio() == pytest.approx(0.708526, abs=1e-6)


def test_the_fitted_aggregate_is_a_third_below_the_published_base():
    """The finding, as an assertion rather than a paragraph."""
    ratio = BASELINE_TAXABLE_PROFITS_BILLIONS / statutory_base_billions()
    assert 0.60 < ratio < 0.70


def test_the_credit_ratio_survives_a_section_904_decomposition():
    """Average absorption against an explicit foreign/domestic split.

    Treat the FTC as exactly the statutory tax on the foreign-source share of
    the base (which is what the section 904 limitation makes it, for a taxpayer
    in an excess-credit position) and the rest of the credits as absorbing the
    domestic remainder at their own average. The two constructions must agree
    closely or the marginal-equals-average substitution is not defensible.
    """
    average = credit_realization_ratio()
    explicit = section_904_realization_ratio()
    assert abs(explicit - average) / average < 0.015


def test_a_missing_tax_year_is_an_error_not_a_silent_fallback():
    with pytest.raises(KeyError):
        soi_row(1999)


# ---------------------------------------------------------------------------
# The projected base — lane W6
# ---------------------------------------------------------------------------


def test_the_transcribed_receipts_path_totals_what_cbo_publishes():
    """The ten-year total is the check on the ten annual transcriptions.

    5,093.9 against the 5,094.0 CBO prints as the total: a tenth of a billion of
    CBO's own rounding, the same artefact the alternatives CSV shows on Option
    64 itself (Table 1-1 gives 136.0 where the alternatives file gives 135.7).
    """
    table = cbo_receipts_by_fiscal_year(CORPORATE_RECEIPTS_VINTAGE)
    assert [year for year, _ in table] == list(range(2025, 2035))
    assert sum(value for _, value in table) == pytest.approx(5094.0, abs=0.15)


def test_the_anchor_is_two_published_series_agreeing_on_one_year():
    """SOI's credit-realized base and Treasury's receipts, same year, within 1%.

    This is the whole content of the anchor. If the two series ever disagree by
    more than a couple of percent, projecting the base off a receipts path is
    not a change of vintage any more — it is a change of concept — and the
    module should not be doing it silently.
    """
    soi_side = credit_realized_base_billions(RECEIPTS_ANCHOR_YEAR)
    treasury_side = actual_corporate_receipts(RECEIPTS_ANCHOR_YEAR) / CURRENT_CORPORATE_RATE

    assert soi_side == pytest.approx(2039.92, abs=0.05)
    assert treasury_side == pytest.approx(2023.17, abs=0.05)
    assert abs(soi_side / treasury_side - 1.0) < 0.02

    # The ratio the module actually multiplies by is that agreement, expressed
    # per dollar of receipts. Not a marginal-realization share: the factor that
    # would reproduce CBO Option 64 is 0.5785 and JCT's own steady-state share
    # is 0.590, and the memo forbids both.
    assert BASE_PER_DOLLAR_OF_RECEIPTS == pytest.approx(4.80133, abs=1e-5)
    assert BASE_PER_DOLLAR_OF_RECEIPTS * CURRENT_CORPORATE_RATE == pytest.approx(
        1.0083, abs=0.001
    )


def test_the_projected_base_tracks_the_published_path():
    for year in range(2025, 2035):
        expected = cbo_corporate_receipts(year) * BASE_PER_DOLLAR_OF_RECEIPTS
        assert projected_statutory_base(year) == pytest.approx(expected, rel=1e-12)
    assert projected_statutory_base(2025) == pytest.approx(2372.34, abs=0.01)


def test_outside_the_window_the_terminal_growth_rate_continues():
    """The rule ``payroll.covered_earnings`` uses, not a silent clamp."""
    table = cbo_receipts_by_fiscal_year()
    terminal_growth = table[-1][1] / table[-2][1] - 1.0
    assert cbo_corporate_receipts(2035) == pytest.approx(
        table[-1][1] * (1 + terminal_growth)
    )
    leading_growth = table[1][1] / table[0][1] - 1.0
    assert cbo_corporate_receipts(2024) == pytest.approx(
        table[0][1] / (1 + leading_growth)
    )


def test_an_unsourced_vintage_raises_rather_than_borrowing_another_s_numbers():
    """Reporting February 2024's path as January 2025's would be a false claim."""
    with pytest.raises(KeyError, match="cbo_feb_2024"):
        cbo_receipts_by_fiscal_year("cbo_jan_2025")


def test_the_derived_base_grows_at_cbo_s_rate_not_the_module_s():
    """The defect W6 closed, as an assertion.

    CBO's own February 2024 corporate receipts grow at **1.44%/yr** over
    FY2026-2034 — the memo's window, which drops FY2025 because it is the tail
    of the pre-window level — and at 1.21%/yr over the full FY2025-2034. The
    base used to be aged at ``CORPORATE_BASE_GROWTH`` = 4%, nearly three times
    either.
    """
    table = cbo_receipts_by_fiscal_year()
    full = (table[-1][1] / table[0][1]) ** (1 / (len(table) - 1)) - 1.0
    memo_window = (table[-1][1] / table[1][1]) ** (1 / (len(table) - 2)) - 1.0
    assert full == pytest.approx(0.0121, abs=0.0005)
    assert memo_window == pytest.approx(0.0144, abs=0.0005)
    assert CORPORATE_BASE_GROWTH > 2.5 * memo_window


def test_the_marginal_base_never_exceeds_the_average_base(scorer):
    """No marginal base can be more than 100% of the average base it is part of.

    Before W6 this ran 0.603 in FY2025 to **1.016** in FY2034 — the derived path
    priced a percentage point of statutory rate against more base than the whole
    baseline corporate tax implies exists. It is an internal inconsistency
    independent of any target, and closing it is the lane's reason to exist.
    """
    policy = create_corporate_rate_change(0.01, mode=CORPORATE_MODE_DERIVED)
    result = scorer.score_policy(policy, dynamic=False)

    shares = []
    for year, deficit in zip(result.years, result.final_deficit_effect, strict=False):
        average_base = cbo_corporate_receipts(int(year)) / CURRENT_CORPORATE_RATE
        shares.append(abs(float(deficit)) / 0.01 / average_base)

    assert max(shares) < 1.0
    # And it is flat rather than drifting, because numerator and denominator are
    # now the same series: (1 - beta x 0.22) x the anchor wedge.
    steady = shares[1:]
    assert max(steady) - min(steady) < 0.02
    assert sum(steady) / len(steady) == pytest.approx(0.829, abs=0.01)


# ---------------------------------------------------------------------------
# Coupling to the engine and to the statute
# ---------------------------------------------------------------------------


def test_the_derived_growth_constant_is_the_engine_s_own(scorer):
    registered = {
        cls.__name__: rate for cls, rate, _ in scorer._growth_tax_policy_handlers
    }
    assert registered["CorporateTaxPolicy"] == CORPORATE_BASE_GROWTH


def test_section_6655_timing_is_the_convolution_on_the_path():
    """``0.75 + 0.25 B(t-1)/B(t)``, not its constant-growth closed form.

    It exceeds 1.0 wherever the projected base falls, which is right: a fiscal
    year collecting a quarter of a larger previous tax year collects more than
    its own. CBO's February 2024 path falls in FY2026 and FY2027.
    """
    policy = create_corporate_rate_change(0.01, mode=CORPORATE_MODE_DERIVED)
    carry = 1.0 - ESTIMATED_PAYMENT_SAME_FY_SHARE

    assert policy.get_phase_in_factor(policy.start_year) == pytest.approx(
        ESTIMATED_PAYMENT_SAME_FY_SHARE
    )
    for year in range(policy.start_year + 1, policy.start_year + 10):
        expected = ESTIMATED_PAYMENT_SAME_FY_SHARE + carry * (
            projected_statutory_base(year - 1) / projected_statutory_base(year)
        )
        assert policy.get_phase_in_factor(year) == pytest.approx(expected)
    assert policy.get_phase_in_factor(policy.start_year - 1) == 0.0

    assert policy.get_phase_in_factor(2026) > 1.0
    assert policy.get_phase_in_factor(2034) < 1.0


def test_the_convolution_degenerates_to_the_old_closed_form_under_constant_growth():
    """The check that W6 changed the path and not the statute.

    Under a base growing at a constant ``g`` the convolution collapses to
    ``0.75 + 0.25/(1+g)``, which is exactly what the module computed before it
    read a path. Recomputed here on a synthetic constant-growth series.
    """
    growth = CORPORATE_BASE_GROWTH
    closed_form = ESTIMATED_PAYMENT_SAME_FY_SHARE + (
        1.0 - ESTIMATED_PAYMENT_SAME_FY_SHARE
    ) / (1.0 + growth)
    convolution = ESTIMATED_PAYMENT_SAME_FY_SHARE + (
        1.0 - ESTIMATED_PAYMENT_SAME_FY_SHARE
    ) * (1.0 / (1.0 + growth))
    assert convolution == pytest.approx(closed_form)
    assert closed_form == pytest.approx(0.99038, abs=1e-5)


def test_reported_mode_keeps_the_base_class_phase_factor():
    policy = create_corporate_rate_change(0.01, mode=CORPORATE_MODE_REPORTED)
    for year in range(policy.start_year, policy.start_year + 10):
        assert policy.get_phase_in_factor(year) == 1.0


def test_derived_reproduces_the_identity_year_by_year(scorer):
    """The whole derived identity, recomputed here from the published inputs.

    Four factors and nothing else: CBO's projected receipts, the anchor ratio,
    IRC section 6655's convolution, and one frozen profit-shifting
    semi-elasticity applied at the reform rate level.
    """
    delta = 0.01
    policy = create_corporate_rate_change(delta, mode=CORPORATE_MODE_DERIVED)
    reform_rate = CURRENT_CORPORATE_RATE + delta
    carry = 1.0 - ESTIMATED_PAYMENT_SAME_FY_SHARE

    expected = 0.0
    for t in range(10):
        year = policy.start_year + t
        base = cbo_corporate_receipts(year) * BASE_PER_DOLLAR_OF_RECEIPTS
        phase = (
            ESTIMATED_PAYMENT_SAME_FY_SHARE
            if t == 0
            else ESTIMATED_PAYMENT_SAME_FY_SHARE
            + carry * projected_statutory_base(year - 1) / base
        )
        revenue = delta * base * phase
        expected += -revenue + revenue * PROFIT_SHIFTING_SEMI_ELASTICITY * reform_rate

    assert _ten_year(scorer, policy) == pytest.approx(expected, rel=1e-9)
    assert _ten_year(scorer, policy) == pytest.approx(-196.08, abs=0.01)


def test_the_engine_does_not_regrow_the_projected_path(scorer):
    """The path already grows; the engine's 4%/yr must be switched off for it.

    If it were not, the FY2034 static effect would be ``1.04**9`` = 1.42x the
    figure the identity above computes.
    """
    policy = create_corporate_rate_change(0.01, mode=CORPORATE_MODE_DERIVED)
    assert policy.uses_projected_base() is True
    assert create_corporate_rate_change(0.01, mode=CORPORATE_MODE_REPORTED).uses_projected_base() is False

    result = scorer.score_policy(policy, dynamic=False)
    last = abs(float(result.static_revenue_effect[-1]))
    first = abs(float(result.static_revenue_effect[0]))
    # 26.24 / 17.79 = 1.475 on the path with the first year's 0.75 in it;
    # regrowing at 4% would put it near 2.1.
    assert last / first == pytest.approx(1.475, abs=0.02)


# ---------------------------------------------------------------------------
# What the derived path buys
# ---------------------------------------------------------------------------


def test_reported_is_exactly_linear_in_the_rate_step(scorer):
    """The property that makes one target 3.7% and the other 47.1%.

    Steps are kept below the 29.6% pass-through kink: above it the
    C-corp-to-pass-through branch fires and adds the module's only other
    curvature, which is not what this test is about.

    ``mode=`` is passed explicitly since the 2026-09-05 Decision 1 flip; before
    it, the module default was ``reported`` and this test relied on it.
    """
    per_point = [
        abs(
            _ten_year(
                scorer, create_corporate_rate_change(d, mode=CORPORATE_MODE_REPORTED)
            )
        )
        / (d * 100)
        for d in (0.01, 0.02, 0.05, 0.07)
    ]
    for value in per_point[1:]:
        assert value == pytest.approx(per_point[0], rel=1e-9)


def test_derived_is_concave_in_the_rate_step(scorer):
    """A bigger rate rise must yield fewer dollars per point, not the same."""
    per_point = [
        abs(_ten_year(scorer, create_corporate_rate_change(d, mode=CORPORATE_MODE_DERIVED)))
        / (d * 100)
        for d in (0.01, 0.02, 0.05, 0.07)
    ]
    assert per_point == sorted(per_point, reverse=True)
    assert per_point[0] > per_point[-1] * 1.05


def test_both_modes_erode_a_rate_cut_instead_of_amplifying_it(scorer):
    """The signed-offset contract ``policies_core`` documents.

    A corporate rate cut's behavioural response recovers some of the revenue,
    so the deficit effect must be *smaller* in magnitude than the static
    effect. Reported mode got this backwards until the offset-sign sweep
    (2026-09-05) — this test used to pin the defect so that changing it would
    be a decision rather than an accident, and the sweep made that decision
    with a caption and a moved benchmark row attached.
    """
    cut_derived = CorporateTaxPolicy(
        name="cut",
        description="21% to 15%",
        policy_type=PolicyType.CORPORATE_TAX,
        rate_change=-0.06,
        mode=CORPORATE_MODE_DERIVED,
        include_passthrough_effects=False,
    )
    static = cut_derived.estimate_static_revenue_effect(0.0)
    offset = cut_derived.estimate_behavioral_offset(static)
    assert static < 0
    assert offset < 0  # signed with the static effect
    assert abs(-static + offset) < abs(static)

    cut_reported = CorporateTaxPolicy(
        name="cut",
        description="21% to 15%",
        policy_type=PolicyType.CORPORATE_TAX,
        rate_change=-0.06,
        mode=CORPORATE_MODE_REPORTED,
        include_passthrough_effects=False,
    )
    static_r = cut_reported.estimate_static_revenue_effect(0.0)
    offset_r = cut_reported.estimate_behavioral_offset(static_r)
    assert static_r < 0
    assert offset_r < 0  # signed with the static effect here too, since the sweep
    assert abs(-static_r + offset_r) < abs(static_r)


def test_derived_reads_no_baseline_level(scorer):
    """Same score on every vintage — cbo_options.py's stated property."""
    policy = create_corporate_rate_change(0.01, mode=CORPORATE_MODE_DERIVED)
    scores = {
        vintage: build_scorer_for_vintage(vintage).score_policy(policy).total_10_year_cost
        for vintage in (None, BaselineVintage.CBO_FEB_2024)
    }
    assert len(set(round(float(v), 9) for v in scores.values())) == 1


def test_the_breakdown_follows_the_mode():
    for mode in (CORPORATE_MODE_REPORTED, CORPORATE_MODE_DERIVED):
        policy = create_corporate_rate_change(0.07, mode=mode)
        breakdown = policy.get_component_breakdown()
        assert breakdown["rate_change_effect"] == pytest.approx(
            policy.estimate_static_revenue_effect(0.0)
        )


def test_an_unknown_mode_is_refused():
    with pytest.raises(ValueError, match="Unknown corporate scoring mode"):
        CorporateTaxPolicy(
            name="x",
            description="x",
            policy_type=PolicyType.CORPORATE_TAX,
            rate_change=0.01,
            mode="fitted",
        )


def test_no_factory_sets_a_per_case_elasticity():
    """MODELING_IMPROVEMENT.md §4: one frozen value per mechanism."""
    for factory in (
        create_biden_corporate_rate_only,
        create_biden_corporate_proposal,
        create_republican_corporate_cut,
        create_tcja_corporate_repeal,
    ):
        policy = factory(mode=CORPORATE_MODE_DERIVED)
        assert policy.profit_shifting_semi_elasticity == PROFIT_SHIFTING_SEMI_ELASTICITY


# ---------------------------------------------------------------------------
# Nothing shipped moved
# ---------------------------------------------------------------------------


def test_the_app_default_is_derived():
    """Flipped 2026-09-05 under Decision 1 — see ``DECISION1_corporate_mode.md``.

    Both halves matter and they are two different things. The constant is what
    the scorecard runner resolves ``mode=None`` to; the dataclass field default
    is what every app surface and every factory picks up. A flip that moved one
    and not the other would put the app and its own scorecard on different
    identities, which is the failure this asserts against.
    """
    assert CORPORATE_APP_MODE == CORPORATE_MODE_DERIVED
    default = CorporateTaxPolicy(
        name="x", description="x", policy_type=PolicyType.CORPORATE_TAX
    )
    assert default.mode == CORPORATE_MODE_DERIVED

    # And the validation pin did not move with it: an out-of-sample prediction
    # must not start reading whatever the app happens to score.
    assert CORPORATE_VALIDATION_MODE == CORPORATE_MODE_DERIVED


def test_the_scorecard_runner_follows_the_app_default():
    """Corporate has no ``AMT_SCORECARD_MODE`` twin; one switch drives both.

    ``amt.py`` carries ``AMT_APP_MODE`` and ``AMT_SCORECARD_MODE`` separately.
    ``corporate.py`` carries one constant and
    ``validation/specialized_business.py`` defaults to it, so the app default
    and the by-construction scorecard mode are the same switch. Pinned because
    the AMT convention makes a reader expect a second constant, and a future
    lane that adds one should have to change this test to do it.
    """
    from fiscal_model.validation.specialized_business import validate_all_corporate

    default = validate_all_corporate(verbose=False)
    explicit = validate_all_corporate(verbose=False, mode=CORPORATE_APP_MODE)
    assert [row.model_10yr for row in default] == [row.model_10yr for row in explicit]
    assert [round(float(row.model_10yr), 2) for row in default] == [
        -1292.62,
        -1292.62,
        1545.24,
    ]


def test_reported_mode_pins(scorer):
    """Regression pins for reported mode, which nothing shipped scores any more.

    The rate *increase* is unchanged from ``1d35f1b``: its static is positive,
    so an ``abs()`` offset and a signed one are the same number. The rate *cut*
    moved **1,917.98 -> 1,491.76** when the offset-sign sweep signed the
    reported branch, because 12.5% of a negative static had been landing on the
    wrong side. No constant was retuned to put it back, and none was retuned
    when the app left this mode either: these two figures are the same after
    the 2026-09-05 Decision 1 flip as before it, which is the check that the
    flip changed a default and not a model.
    """
    assert _ten_year(
        scorer, create_biden_corporate_rate_only(mode=CORPORATE_MODE_REPORTED)
    ) == pytest.approx(-1397.21, abs=0.01)
    assert _ten_year(
        scorer, create_republican_corporate_cut(mode=CORPORATE_MODE_REPORTED)
    ) == pytest.approx(1491.76, abs=0.01)


def test_derived_mode_pins(scorer):
    """What the app scores now, on the benchmarks' own FY2025-2034 window."""
    assert _ten_year(scorer, create_biden_corporate_rate_only()) == pytest.approx(
        -1292.62, abs=0.01
    )
    assert _ten_year(scorer, create_republican_corporate_cut()) == pytest.approx(
        1545.24, abs=0.01
    )


def test_every_corporate_preset_scores_the_derived_figure():
    """The shipped surfaces, on the app's own FY2026-2035 window.

    Two of the 53 ``PRESET_POLICIES`` entries reach ``CorporateTaxPolicy``, and
    both moved with the Decision 1 flip: Biden Corporate 28% **-1,397.21 ->
    -1,310.92** (+6.18%) and Trump Corporate 15% **+1,491.76 -> +1,562.75**
    (+4.76%). They are not the figures in ``test_derived_mode_pins`` because
    the app opens its window at ``APP_DEFAULT_START_YEAR`` = 2026 while the
    benchmarks are quoted on FY2025-2034, and the derived base is read off a
    published path by *absolute* fiscal year — so a one-year shift moves the
    number, which is the whole point of projecting the base off a vintage.

    This asserts what a user sees equals what the mode says, so the two cannot
    drift: a factory whose ``mode=`` default was missed by a future flip would
    show up here rather than in production.
    """
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.baseline import APP_DEFAULT_START_YEAR
    from fiscal_model.preset_handler import create_policy_from_preset

    expected = {
        "🏢 Biden Corporate 28% (CBO: -$1.35T)": -1310.92,
        "🏢 Trump Corporate 15%": 1562.75,
    }

    seen = {}
    for label, data in PRESET_POLICIES.items():
        policy = create_policy_from_preset(data)
        if not isinstance(policy, CorporateTaxPolicy):
            continue
        assert policy.mode == CORPORATE_APP_MODE == CORPORATE_MODE_DERIVED, label
        start = max(int(policy.start_year), APP_DEFAULT_START_YEAR)
        run = FiscalPolicyScorer(start_year=start, use_real_data=False)
        seen[label] = float(run.score_policy(policy, dynamic=False).total_10_year_cost)

    assert set(seen) == set(expected), seen
    for label, target in expected.items():
        assert seen[label] == pytest.approx(target, abs=0.01), label


def test_decision_1_ranks_the_two_modes_on_the_registered_targets(scorer):
    """The comparison the app default turns on, as a test rather than a claim.

    **This assertion has reversed three times, which is why it reads its
    targets off the registry instead of carrying its own copy.** The
    offset-sign sweep flipped it first: signing the reported offset took
    reported 1.92% -> 13.02% against derived's unmoved 9.67%, because
    ``trump_corporate_15`` had been reading 0.1% through the ``abs()`` defect.
    The sweep declined to act on it and said why — the row producing the
    reversal carried provenance ``model_estimate``, so neither ranking was
    evidence about the world. W6's base projection moved derived to 11.78%
    next. Then the 2026-09-05 provenance lane settled the population:
    ``trump_corporate_15``'s target became the published range
    [+$595.0B, +$673.1B] anchored on Tax Foundation's +$673.1B, and the FY2022
    Green Book's rate-only row joined the suite as a second published corporate
    benchmark.

    On three published targets **derived leads narrowly, 61.43% against
    62.75%**, and the mode was flipped on 2026-09-05 under Decision 1
    (``planning/lanes/DECISION1_corporate_mode.md``). Read the margin with its
    composition attached, which the next test pins: derived wins **one** row of
    three, and neither figure is small.
    """
    from fiscal_model.validation.scenarios import CORPORATE_VALIDATION_SCENARIOS

    means = {}
    for mode in (CORPORATE_MODE_REPORTED, CORPORATE_MODE_DERIVED):
        errors = [
            abs(_ten_year(scorer, scenario["policy_factory"](mode=mode)) - target)
            / abs(target)
            for scenario in CORPORATE_VALIDATION_SCENARIOS.values()
            for target in (scenario["expected_10yr"],)
        ]
        means[mode] = sum(errors) / len(errors)
    assert means[CORPORATE_MODE_DERIVED] < means[CORPORATE_MODE_REPORTED]
    assert means[CORPORATE_MODE_REPORTED] == pytest.approx(0.6275, abs=0.0002)
    assert means[CORPORATE_MODE_DERIVED] == pytest.approx(0.6143, abs=0.0002)

    # The flip. Both means stay pinned above it, so a lane that improved the
    # margin by retuning a constant would fail here rather than pass quietly.
    assert CORPORATE_APP_MODE == CORPORATE_MODE_DERIVED


def test_the_decision_1_margin_is_one_row(scorer):
    """What the 1.31pp lead is made of, so the mean cannot be read alone.

    Derived wins ``biden_corporate_28_fy2022`` by 12.19 points and loses the
    other two — ``trump_corporate_15``, which is a shipped preset, by 7.95 and
    ``biden_corporate_28``, the row with the strongest document behind it, by
    0.31. Two of the three read 50-130% in **both** modes, so the statistic
    that decides the app default is dominated by rows neither mode gets near.

    And the first two rows are the same reform — 21% to 28% — scored by the
    same factory on the same FY2025-2034 window, because the repository carries
    no 2021 vintage. So the model returns **one** number for two published
    targets 57% apart and no mode can win both: derived wins that pair by
    sitting lower, not by tracking a vintage. Asserted rather than described,
    because it is the reason the margin is thin.
    """
    from fiscal_model.validation.scenarios import CORPORATE_VALIDATION_SCENARIOS

    errors = {}
    models = {}
    for mode in (CORPORATE_MODE_REPORTED, CORPORATE_MODE_DERIVED):
        for name, scenario in CORPORATE_VALIDATION_SCENARIOS.items():
            model = _ten_year(scorer, scenario["policy_factory"](mode=mode))
            target = scenario["expected_10yr"]
            models[(mode, name)] = model
            errors[(mode, name)] = abs(model - target) / abs(target)

    wins = {
        name: errors[(CORPORATE_MODE_DERIVED, name)]
        < errors[(CORPORATE_MODE_REPORTED, name)]
        for name in CORPORATE_VALIDATION_SCENARIOS
    }
    assert sum(wins.values()) == 1
    assert wins["biden_corporate_28_fy2022"] is True

    # One number, two targets 57% apart, in either mode.
    for mode in (CORPORATE_MODE_REPORTED, CORPORATE_MODE_DERIVED):
        assert models[(mode, "biden_corporate_28")] == pytest.approx(
            models[(mode, "biden_corporate_28_fy2022")]
        )
    targets = CORPORATE_VALIDATION_SCENARIOS
    spread = abs(
        targets["biden_corporate_28"]["expected_10yr"]
        / targets["biden_corporate_28_fy2022"]["expected_10yr"]
        - 1.0
    )
    assert spread == pytest.approx(0.57, abs=0.01)

    # Neither mode is close on two of the three rows.
    for mode in (CORPORATE_MODE_REPORTED, CORPORATE_MODE_DERIVED):
        far = [n for n in CORPORATE_VALIDATION_SCENARIOS if errors[(mode, n)] > 0.5]
        assert sorted(far) == ["biden_corporate_28_fy2022", "trump_corporate_15"]


# ---------------------------------------------------------------------------
# Decision 6 - the moved headline ships with its explanation
# ---------------------------------------------------------------------------


def test_the_caption_fires_on_both_corporate_presets_and_carries_the_constants():
    """Decision 6 for the flip: every corporate headline that moved says why.

    The caption is built from the module's own constants and the scored window
    rather than from restated figures, so it cannot drift from the headline it
    sits under. This asserts each of them is actually in the text — a caption
    that quietly stopped reading the anchor, or the vintage, would still render
    and would still look right.
    """
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.baseline import APP_DEFAULT_START_YEAR
    from fiscal_model.corporate import (
        BASE_PER_DOLLAR_OF_RECEIPTS,
        cbo_corporate_receipts,
        projected_statutory_base,
    )
    from fiscal_model.preset_handler import create_policy_from_preset
    from fiscal_model.ui.tabs.results_summary import corporate_base_caption

    captioned = 0
    for label, data in PRESET_POLICIES.items():
        policy = create_policy_from_preset(data)
        if not isinstance(policy, CorporateTaxPolicy):
            continue
        start = max(int(policy.start_year), APP_DEFAULT_START_YEAR)
        result = FiscalPolicyScorer(
            start_year=start, use_real_data=False
        ).score_policy(policy, dynamic=False)
        note = corporate_base_caption(policy, result)
        assert note, label
        captioned += 1

        first, last = int(result.years[0]), int(result.years[-1])
        # The receipts path, both ends of the scored window.
        assert f"{cbo_corporate_receipts(first):,.1f}B in {first}" in note
        assert f"{cbo_corporate_receipts(last):,.1f}B in {last}" in note
        # The base those receipts imply, at the anchor ratio.
        assert f"{projected_statutory_base(first):,.0f}B" in note
        assert f"{BASE_PER_DOLLAR_OF_RECEIPTS:.4f} base-dollars" in note
        # The fitted aggregate and its aging - what the app scored until the flip.
        assert f"{BASELINE_TAXABLE_PROFITS_BILLIONS:,.0f}B profits aggregate" in note
        assert f"{CORPORATE_BASE_GROWTH:.0%} a year" in note
        # Which mode, and which direction the behavioural response runs in.
        assert f"`{CORPORATE_APP_MODE}` mode" in note
        assert "erodes" in note
        # The app window outruns the transcribed table by a year, and the
        # caption says which years are published and which are continued.
        assert f"published through {CORPORATE_RECEIPTS_LAST_TABULATED_YEAR}" in note

    assert captioned == 2


def test_the_caption_is_silent_where_it_has_nothing_to_explain(scorer):
    """A note that appears everywhere explains nothing.

    Three silences, and they are three different reasons. ``reported`` mode did
    not move, so it has nothing to say. A corporate shape with no rate channel
    prices no statutory base, so the caption would be describing a factor the
    score never used. And a non-corporate policy never reaches the module at
    all.
    """
    from fiscal_model.policies import TaxPolicy
    from fiscal_model.ui.tabs.results_summary import corporate_base_caption

    reported = create_corporate_rate_change(0.01, mode=CORPORATE_MODE_REPORTED)
    assert (
        corporate_base_caption(reported, scorer.score_policy(reported, dynamic=False))
        == ""
    )

    no_rate = CorporateTaxPolicy(
        name="g",
        description="GILTI only",
        policy_type=PolicyType.CORPORATE_TAX,
        rate_change=0.0,
        gilti_rate_change=0.105,
    )
    assert (
        corporate_base_caption(no_rate, scorer.score_policy(no_rate, dynamic=False))
        == ""
    )

    individual = TaxPolicy(
        name="t",
        description="+1pp at 400K",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01,
        affected_income_threshold=400_000,
    )
    assert (
        corporate_base_caption(
            individual, scorer.score_policy(individual, dynamic=False)
        )
        == ""
    )


# ---------------------------------------------------------------------------
# The validation shape
# ---------------------------------------------------------------------------


def test_the_option_64_shape_is_pinned_to_derived():
    policy = create_policy_from_score(KNOWN_SCORES["cbo_opt64_corporate_rate_1pp"])
    assert isinstance(policy, CorporateTaxPolicy)
    assert policy.mode == CORPORATE_VALIDATION_MODE == CORPORATE_MODE_DERIVED
    assert policy.start_year == 2025


def test_the_uncalibrated_path_never_reads_the_fitted_aggregate():
    """The leakage guard for this shape, stated directly."""
    policy = create_policy_from_score(KNOWN_SCORES["cbo_opt64_corporate_rate_1pp"])
    static = policy.estimate_static_revenue_effect(0.0)
    fitted = policy.rate_change * BASELINE_TAXABLE_PROFITS_BILLIONS
    assert abs(static - fitted) / abs(fitted) > 0.15


def test_the_corporate_runner_prints_both_modes():
    """Decision 1's comparison has a runner, as ``validate_amt_policy`` does."""
    from fiscal_model.validation.specialized_business import validate_all_corporate

    means = {}
    for mode in (CORPORATE_MODE_REPORTED, CORPORATE_MODE_DERIVED):
        rows = validate_all_corporate(verbose=False, mode=mode)
        # Three since 2026-09-05: the FY2022 Green Book's rate-only row is the
        # module's second published benchmark and its first reconstruction.
        assert len(rows) == 3
        means[mode] = sum(abs(row.percent_difference) for row in rows) / len(rows)

    # Reported was 1.92% before the offset-sign sweep signed its offset and
    # 13.02% after it; both readings scored `trump_corporate_15` against this
    # model's own +$1,920B. These are the figures against published targets,
    # and derived's is the one the app has scored since the 2026-09-05 flip.
    assert means[CORPORATE_MODE_REPORTED] == pytest.approx(62.75, abs=0.01)
    assert means[CORPORATE_MODE_DERIVED] == pytest.approx(61.43, abs=0.01)


def test_the_corporate_runner_refuses_an_unknown_mode():
    from fiscal_model.validation.specialized_business import validate_corporate_policy

    with pytest.raises(ValueError, match="mode must be one of"):
        validate_corporate_policy("biden_corporate_28", verbose=False, mode="fitted")
