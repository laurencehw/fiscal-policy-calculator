"""H3a — the corporate estimator range, and the five ways it can be wrong.

Lane doc: ``planning/lanes/HSB_h3a_corporate_range.md``. The lane is
presentation only, so the tests split into three jobs:

1. **The arithmetic is the memo's.** The shares this helper computes must land
   on ``planning/memos/CORPORATE_PER_POINT_YIELD.md`` section 4b's printed
   table, and the converted totals must reproduce each source's own printed
   figure when converted back to that source's own step. If the helper and the
   memo disagree, the helper is wrong.
2. **The range appears exactly where it should.** For a corporate rate change,
   yes; for an income-tax run, a spending run, or a corporate policy with no
   statutory rate step, no.
3. **Nothing is invented.** Every dollar the helper emits is reconstructed from
   a row of the shipped CSV or from a live ``CalibratedTarget``.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from fiscal_model.corporate import CorporateTaxPolicy
from fiscal_model.policies import PolicyType, SpendingPolicy, TaxPolicy
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.ui.estimator_ranges import (
    CORPORATE_AVERAGE_BASE_BILLIONS_PER_YEAR,
    CORPORATE_RECEIPTS_10YR_BILLIONS,
    CORPORATE_RECORD_PATH,
    CORPORATE_RECORD_WINDOW,
    CORPORATE_STATUTORY_RATE,
    corporate_estimator_range,
    corporate_per_point_record,
    published_range_for,
    scope_verdict_for,
)
from fiscal_model.ui.tabs.results_summary import (
    corporate_estimator_range_captions,
    render_headline_block,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

#: ``CORPORATE_PER_POINT_YIELD.md`` section 4b, and table 3b of
#: ``scripts/corporate_yield_reconciliation.py``: the share of the vintage's
#: average corporate base one statutory point reaches, by estimator. Written out
#: here so a change to the helper's arithmetic has to argue with the memo rather
#: than silently redefine the metric.
MEMO_SECTION_4B_SHARES = {
    "Tax Foundation": 0.551,
    "JCT": 0.559,
    "Penn Wharton Budget Model": 0.644,
    "Treasury OTA": 0.795,
}

#: The same table's reading of this module in the app's shipped mode.
MEMO_MODEL_REPORTED_SHARE = 0.823

#: What the two shipped corporate presets score today, from the lane's
#: before-sweep through ``composer._build_preset_policy``. These are *inputs* to
#: the display, not predictions of it: the lane moves no number, and
#: ``test_no_scored_number_moves``-style falsification is done by the artifact
#: diff in the lane doc rather than here.
BIDEN_28_HEADLINE_BILLIONS = -1397.2107164343076
TRUMP_15_HEADLINE_BILLIONS = 1491.7588100276062


# ---------------------------------------------------------------------------
# 1. The arithmetic is the memo's
# ---------------------------------------------------------------------------


def test_record_selects_exactly_the_memos_four_rows() -> None:
    record = corporate_per_point_record()
    assert len(record) == 4
    assert {y.estimator for y in record} == set(MEMO_SECTION_4B_SHARES)
    assert all(y.published_step_pp for y in record)


def test_shares_reproduce_the_memos_section_4b_table() -> None:
    """Within 0.05pp of the printed table, computed and not transcribed."""
    for yield_ in corporate_per_point_record():
        expected = MEMO_SECTION_4B_SHARES[yield_.estimator]
        assert yield_.marginal_share == pytest.approx(expected, abs=0.0005), (
            f"{yield_.estimator}: helper says {yield_.marginal_share:.4f}, "
            f"the memo prints {expected:.3f}"
        )


def test_average_base_is_cbos_own_receipts_path() -> None:
    """The denominator is publication 59710 Table 1-1, not a fitted level."""
    assert CORPORATE_AVERAGE_BASE_BILLIONS_PER_YEAR == pytest.approx(
        CORPORATE_RECEIPTS_10YR_BILLIONS / CORPORATE_STATUTORY_RATE / 10.0
    )
    assert CORPORATE_AVERAGE_BASE_BILLIONS_PER_YEAR == pytest.approx(2425.7143, abs=1e-3)


def test_baselines_agree_with_the_reconciliation_script() -> None:
    """The one constant not read from the CSV still matches the script's own dict.

    ``scripts/corporate_yield_reconciliation.py`` is the memo's arithmetic and
    imports the whole ``fiscal_model`` package, so it is exercised in a
    subprocess rather than imported: the check is that the two never drift, not
    that either is importable from the other.
    """
    source = (REPO_ROOT / "scripts" / "corporate_yield_reconciliation.py").read_text(
        encoding="utf-8"
    )
    marker = '"cbo_feb_2024": {'
    start = source.index(marker)
    block = source[start : start + 800]
    assert f'"receipts_10yr": {CORPORATE_RECEIPTS_10YR_BILLIONS},' in block
    assert f'"statutory_rate": {CORPORATE_STATUTORY_RATE},' in block
    assert f'"window": "{CORPORATE_RECORD_WINDOW}",' in block


def test_converting_back_to_a_sources_own_step_returns_its_printed_total() -> None:
    """The conversion is an identity at the source's own step, per source."""
    for yield_ in corporate_per_point_record():
        spread = corporate_estimator_range(
            rate_change_pp=yield_.published_step_pp, model_billions=0.0
        )
        assert spread is not None
        match = next(e for e in spread.estimates if e.estimator == yield_.estimator)
        assert match.value_billions == pytest.approx(
            yield_.published_10yr_billions, rel=1e-3
        )


def test_biden_28_range_and_position() -> None:
    spread = corporate_estimator_range(
        rate_change_pp=7.0, model_billions=BIDEN_28_HEADLINE_BILLIONS
    )
    assert spread is not None
    assert spread.low_billions == pytest.approx(-1349.9, abs=0.1)
    assert spread.high_billions == pytest.approx(-935.8, abs=0.1)
    assert spread.model_position == "larger"
    assert spread.distance_to_range_billions == pytest.approx(47.3, abs=0.1)
    # The lane's headline finding: this run prices a point at more of the
    # vintage's average base than any published estimator on the record.
    assert spread.model_marginal_share == pytest.approx(
        MEMO_MODEL_REPORTED_SHARE, abs=0.0005
    )
    assert spread.estimates_below_model_share == 4


def test_trump_15_range_suppresses_the_bundled_share() -> None:
    spread = corporate_estimator_range(
        rate_change_pp=-6.0,
        model_billions=TRUMP_15_HEADLINE_BILLIONS,
        bundled=("100% bonus depreciation",),
    )
    assert spread is not None
    assert spread.low_billions == pytest.approx(802.1, abs=0.1)
    assert spread.high_billions == pytest.approx(1157.1, abs=0.1)
    assert spread.model_position == "larger"
    assert spread.distance_to_range_billions == pytest.approx(334.7, abs=0.1)
    # Naively the share would be 102.5% of the average base, which is not a
    # base defect - it is `extend_bonus_depreciation=True`. Suppressed.
    assert spread.model_marginal_share is None
    assert spread.estimates_below_model_share == 0


def test_share_comparison_is_counted_and_not_asserted() -> None:
    """"Above every published estimator" is step- and mode-dependent.

    ``derived`` at +7pp sits at 76.1% of the average base, below Treasury's
    79.5%. A caption that hard-coded the claim would be wrong there.
    """
    below_treasury = corporate_estimator_range(
        rate_change_pp=7.0,
        # the memo's `model derived +7pp` row, -1,292.62
        model_billions=-1292.62,
    )
    assert below_treasury is not None
    assert below_treasury.model_marginal_share == pytest.approx(0.761, abs=0.001)
    assert below_treasury.estimates_below_model_share == 3


def test_no_rate_step_has_no_per_point_yield() -> None:
    assert corporate_estimator_range(rate_change_pp=0.0, model_billions=220.0) is None


def test_position_reads_magnitude_not_sign() -> None:
    """A deficit-reduction figure below a negative bound is the *larger* effect."""
    inside = corporate_estimator_range(rate_change_pp=7.0, model_billions=-1000.0)
    smaller = corporate_estimator_range(rate_change_pp=7.0, model_billions=-500.0)
    assert inside is not None and smaller is not None
    assert inside.model_position == "inside"
    assert inside.distance_to_range_billions == 0.0
    assert smaller.model_position == "smaller"


# ---------------------------------------------------------------------------
# 2. Purity, and nothing invented
# ---------------------------------------------------------------------------


def test_helper_imports_neither_streamlit_nor_validation_at_module_scope() -> None:
    """The helper's own top-level imports carry neither, read off its AST.

    Asserted on the source rather than on ``sys.modules``, because ``sys.modules``
    cannot see it: importing anything under ``fiscal_model.ui`` runs
    ``fiscal_model/ui/__init__.py``, whose eager re-export chain pulls in the
    whole validation package - see ``test_ui_package_init_is_the_eager_one``,
    which records that separately so this test cannot be quietly satisfied by
    the package doing the import instead.
    """
    import ast

    source = (
        REPO_ROOT / "fiscal_model" / "ui" / "estimator_ranges.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    top_level_imports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level_imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            top_level_imports.append(node.module or "")
    assert top_level_imports, "the module imports nothing at all - test is stale"
    for name in top_level_imports:
        assert not name.startswith("streamlit"), name
        assert not name.startswith("fiscal_model.validation"), name


def test_ui_package_init_is_the_eager_one() -> None:
    """Recorded, not fixed: ``fiscal_model.ui`` imports all of validation.

    A finding of this lane rather than a contract it defends. The helper's own
    lazy import is real and is what Wave C reuses; the package it sits in makes
    it invisible today, and moving that is a cold-start question with a
    different owner. If this test ever fails because the answer became
    ``False``, that is good news - delete it and say so.
    """
    probe = (
        "import sys, fiscal_model.ui.estimator_ranges;"
        "print('fiscal_model.validation' in sys.modules,"
        "'streamlit' in sys.modules)"
    )
    out = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    ).stdout.strip()
    # Streamlit stays out either way, which is the half that matters for a
    # helper Wave C wants to call from a non-Streamlit context.
    assert out.endswith("False"), out


def test_per_point_is_computed_and_agrees_with_the_published_column() -> None:
    """The CSV's rounded column is a cross-check, not the input.

    At Treasury's +7.0pp step the rounded ``per_point_billions`` returns
    -1,349.943 where the source printed -1,349.941 - immaterial in dollars and
    material in trust, because a display that cannot reproduce its own source's
    figure invites the question of what else was rounded.
    """
    for yield_ in corporate_per_point_record():
        assert yield_.per_point_billions == pytest.approx(
            yield_.published_per_point_billions, abs=0.001
        )
        assert yield_.per_point_billions * yield_.published_step_pp == pytest.approx(
            yield_.published_10yr_billions, abs=1e-9
        )


def test_repeated_calls_are_equal() -> None:
    first = corporate_estimator_range(rate_change_pp=7.0, model_billions=-1397.2)
    second = corporate_estimator_range(rate_change_pp=7.0, model_billions=-1397.2)
    assert first == second
    assert corporate_per_point_record() is corporate_per_point_record()


def test_every_emitted_dollar_traces_to_the_shipped_record() -> None:
    """Reconstruct each converted figure from the CSV, independently."""
    with CORPORATE_RECORD_PATH.open(encoding="utf-8") as handle:
        rows = [
            row
            for row in csv.DictReader(
                line for line in handle if not line.startswith("#")
            )
            if row["window"] == CORPORATE_RECORD_WINDOW
        ]
    expected = {
        row["estimator"]: float(row["ten_year_billions"])
        / float(row["rate_change_pp"])
        * 7.0
        for row in rows
    }
    spread = corporate_estimator_range(rate_change_pp=7.0, model_billions=0.0)
    assert spread is not None
    assert {e.estimator: e.value_billions for e in spread.estimates} == pytest.approx(
        expected, rel=1e-9
    )


def test_published_range_is_policy_agnostic() -> None:
    """Wave C's H4 reuses this for Pillar Two and the reciprocal tariffs."""
    trump = published_range_for("trump_corporate_15")
    assert trump is not None
    assert (trump.low_billions, trump.high_billions) == (595.0, 673.1)
    assert not trump.contains(TRUMP_15_HEADLINE_BILLIONS)
    assert trump.distance(TRUMP_15_HEADLINE_BILLIONS) == pytest.approx(818.7, abs=0.1)

    pillar_two = published_range_for("pillar_two_adoption")
    assert pillar_two is not None
    assert (pillar_two.low_billions, pillar_two.high_billions) == (-102.6, 56.5)
    assert pillar_two.contains(-61.2)
    assert pillar_two.distance(-61.2) == 0.0

    tariffs = published_range_for("reciprocal_tariffs")
    assert tariffs is not None
    assert (tariffs.low_billions, tariffs.high_billions) == (-1800.0, -1400.0)

    # A point target is not a range, and an unknown id is not an error.
    assert published_range_for("biden_corporate_28") is None
    assert published_range_for("no_such_benchmark") is None
    assert published_range_for("") is None


def test_scope_verdict_is_read_from_the_registry() -> None:
    biden = scope_verdict_for("biden_corporate_28")
    assert "GILTI" in biden
    assert "gilti_rate_change=0.0" in biden
    trump = scope_verdict_for("trump_corporate_15")
    assert "bonus depreciation" in trump
    # A row whose figures and scope both agree carries no verdict.
    assert scope_verdict_for("biden_corporate_28_fy2022") == ""
    assert scope_verdict_for("") == ""


# ---------------------------------------------------------------------------
# 3. The range appears exactly where it should
# ---------------------------------------------------------------------------


class _Recorder:
    """Enough Streamlit to drive ``render_headline_block`` and read the captions."""

    def __init__(self) -> None:
        self.captions: list[str] = []

    def caption(self, body, *args, **kwargs):
        del args, kwargs
        self.captions.append(str(body))

    def markdown(self, *args, **kwargs):
        del args, kwargs
        return None

    def code(self, *args, **kwargs):
        del args, kwargs
        return None


def _score(policy, *, use_real_data: bool = False, start_year: int = 2025):
    scorer = FiscalPolicyScorer(
        baseline=None, start_year=start_year, use_real_data=use_real_data
    )
    return scorer.score_policy(policy, dynamic=False)


def _rendered_captions(policy, result, policy_name: str = "") -> list[str]:
    recorder = _Recorder()
    scored = SimpleNamespace(
        headline=0.0,
        window="FY2025-FY2034",
        is_spending=isinstance(policy, SpendingPolicy),
        policy_name=policy_name,
        n_years=10,
        baseline_vintage="CBO Feb 2024",
        policy_status="Hypothetical",
        benchmark=None,
        sensitivity=None,
        sensitivity_note="",
        credibility=None,
        tier="generic",
        tier_label="Generic",
        display_name=policy_name or getattr(policy, "name", ""),
        static=0.0,
        behavioral=0.0,
        mode="conventional",
    )
    render_headline_block(
        recorder,
        scored,
        {"policy": policy, "result": result, "policy_name": policy_name},
    )
    return recorder.captions


def _corporate_policy(**kwargs) -> CorporateTaxPolicy:
    defaults = dict(
        name="Test Corporate",
        description="corporate rate change",
        policy_type=PolicyType.CORPORATE_TAX,
        rate_change=0.07,
        start_year=2025,
        duration_years=10,
    )
    defaults.update(kwargs)
    return CorporateTaxPolicy(**defaults)


def test_range_appears_for_a_corporate_rate_run() -> None:
    policy = _corporate_policy()
    captions = _rendered_captions(policy, _score(policy))
    joined = " ".join(captions)
    assert "Estimator range" in joined
    assert "How that range is built" in joined
    # Both bounds, and the four houses.
    for fragment in ("1,349.9", "935.8", "Treasury OTA", "JCT", "Tax Foundation"):
        assert fragment in joined, fragment
    # The memo's own reason the range is a range.
    assert "not comparable across rate levels or scopes" in joined
    assert "GILTI" in joined
    assert "bonus depreciation" in joined


def test_range_does_not_appear_for_an_income_tax_run() -> None:
    policy = TaxPolicy(
        name="Surtax above $400K",
        description="+2pp above $400,000",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02,
        affected_income_threshold=400_000,
        start_year=2025,
        duration_years=10,
    )
    joined = " ".join(_rendered_captions(policy, _score(policy)))
    assert "Estimator range" not in joined


def test_range_does_not_appear_for_a_spending_run() -> None:
    policy = SpendingPolicy(
        name="Discretionary cut",
        description="cut discretionary spending",
        policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
        annual_spending_change_billions=-50.0,
        start_year=2025,
        duration_years=10,
    )
    joined = " ".join(_rendered_captions(policy, _score(policy)))
    assert "Estimator range" not in joined


def test_range_does_not_appear_for_a_corporate_policy_with_no_rate_step() -> None:
    """The corporate AMT shape: a corporate policy that moves no statutory rate.

    A per-point yield has nothing to multiply, so the caption must stay silent
    rather than convert a zero step into a zero range.
    """
    policy = _corporate_policy(
        name="Repeal corporate AMT",
        rate_change=0.0,
        adjust_book_minimum=True,
        book_minimum_rate_change=-0.15,
    )
    assert (
        corporate_estimator_range_captions(policy, _score(policy), "Repeal corporate AMT")
        == ()
    )


def test_new_rate_is_converted_on_the_step_it_is_scored_at() -> None:
    """A policy stating ``new_rate`` rather than ``rate_change`` still converts."""
    policy = _corporate_policy(rate_change=0.0, new_rate=0.28)
    captions = corporate_estimator_range_captions(policy, _score(policy))
    assert captions
    assert "+7.0pp" in captions[0]


def test_biden_28_caption_reads_as_the_lane_predicted() -> None:
    policy = _corporate_policy(name="Biden Corporate Rate to 28%")
    captions = corporate_estimator_range_captions(
        policy,
        _score(policy),
        "🏢 Biden Corporate 28% (CBO: -$1.35T)",
    )
    joined = " ".join(captions)
    # The scope verdict, read live from the benchmark registry.
    assert "price different reforms" in joined
    assert "gilti_rate_change=0.0" in joined
    # ...and no published range, because this row's target is a point.
    assert "carries a published range" not in joined


def test_trump_15_caption_shows_the_published_range_and_the_non_overlap() -> None:
    policy = _corporate_policy(
        name="Trump Corporate Rate Cut",
        rate_change=-0.06,
        extend_bonus_depreciation=True,
    )
    captions = corporate_estimator_range_captions(
        policy, _score(policy), "🏢 Trump Corporate 15%"
    )
    joined = " ".join(captions)
    assert "carries a published range" in joined
    assert "+595.0B" in joined and "+673.1B" in joined
    assert "do **not** overlap" in joined
    # The bundled run does not quote a model share.
    assert "share of the vintage's average corporate base" not in joined
    assert "100% bonus depreciation" in joined


def test_currency_is_escaped_so_katex_does_not_eat_it() -> None:
    """Every ``$`` before a digit carries its markdown escape.

    An unescaped ``$-1,349.9B to $`` renders as an italic math span with the
    dollar signs eaten - caught in a browser once already, on the sensitivity
    band a few lines below this caption.
    """
    policy = _corporate_policy(name="Trump Corporate Rate Cut", rate_change=-0.06)
    captions = corporate_estimator_range_captions(
        policy, _score(policy), "🏢 Trump Corporate 15%"
    )
    assert captions
    for caption in captions:
        for index, char in enumerate(caption):
            if char == "$" and index + 1 < len(caption):
                following = caption[index + 1]
                if following.isdigit() or following in "+-":
                    assert index and caption[index - 1] == "\\", caption[
                        max(0, index - 30) : index + 30
                    ]
