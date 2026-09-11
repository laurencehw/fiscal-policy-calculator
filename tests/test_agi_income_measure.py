"""Which IRS SOI income column a policy's base is read from.

``TaxPolicy.ordinary_income_base`` answers *is the preferential (LTCG/QDIV)
share removed?*; ``TaxPolicy.income_measure`` answers *which column is the base
in the first place?* SOI Table 1.1's rows are AGI size classes and it publishes
both, so a surtax whose source states it on AGI was priced by subtracting an AGI
threshold from an average of taxable income - the same returns and the same
floor, but two different quantities.

See ``planning/lanes/HSB_h2b_agi_column.md``.
"""

import pytest

from fiscal_model import policies_core
from fiscal_model.data import irs_soi
from fiscal_model.data.irs_soi import FILING_STATUSES, INCOME_MEASURES, IRSSOIData
from fiscal_model.policies import (
    DEFAULT_INCOME_MEASURE,
    INCOME_MEASURE_AGI,
    INCOME_MEASURE_TAXABLE_INCOME,
    PolicyType,
    TaxPolicy,
    income_measure_for_preset,
)
from fiscal_model.validation.cbo_scores import KNOWN_SCORES
from fiscal_model.validation.core import (
    _AGI_BASE_POLICY_IDS,
    AGI_BASE_RULE,
    agi_base_source_sentence,
    create_policy_from_score,
    validation_shape,
)

SOI_YEAR = 2023


def _policy(**kwargs) -> TaxPolicy:
    params = {
        "name": "probe",
        "description": "probe",
        "policy_type": PolicyType.INCOME_TAX,
        "rate_change": 0.01,
        "affected_income_threshold": 400_000.0,
        "start_year": 2025,
        "duration_years": 10,
    }
    params.update(kwargs)
    return TaxPolicy(**params)


# -- the attribute and its invariant ------------------------------------------


def test_the_default_measure_is_taxable_income():
    """Every policy that declares nothing behaves exactly as it did before."""
    assert DEFAULT_INCOME_MEASURE == INCOME_MEASURE_TAXABLE_INCOME
    assert _policy().income_measure == INCOME_MEASURE_TAXABLE_INCOME
    assert TaxPolicy.__dataclass_fields__["income_measure"].default == (
        INCOME_MEASURE_TAXABLE_INCOME
    )


def test_an_unknown_measure_is_refused():
    with pytest.raises(ValueError, match="income_measure must be"):
        _policy(income_measure="magi")


def test_an_agi_base_refuses_the_ordinary_correction():
    """AGI already contains the income the ordinary correction removes.

    The reverse is deliberately NOT an invariant: ``ordinary_income_base=False``
    on a taxable-income base is a real classification (TPC's illustrative
    surtaxes), which is why these are two attributes and not one.
    """
    with pytest.raises(ValueError, match="requires the AGI-inclusive base"):
        _policy(income_measure=INCOME_MEASURE_AGI, ordinary_income_base=True)

    ok = _policy(income_measure=INCOME_MEASURE_AGI, ordinary_income_base=False)
    assert ok.income_measure == INCOME_MEASURE_AGI

    also_ok = _policy(
        income_measure=INCOME_MEASURE_TAXABLE_INCOME, ordinary_income_base=False
    )
    assert also_ok.income_measure == INCOME_MEASURE_TAXABLE_INCOME


def test_the_two_modules_declare_the_same_measures():
    """Two declarations, one meaning, and a test so they cannot drift.

    ``policies_core`` must not import ``data.irs_soi`` at file scope - that
    pulls pandas into the app's import graph and moves the cold-start figures
    ``tests/test_cold_start_ordering.py`` pins - so each declares the names it
    needs. This is the gate that makes the duplication safe: adding a third
    column, or renaming one, in only one of them fails here.
    """
    assert policies_core.INCOME_MEASURES == irs_soi.INCOME_MEASURES
    assert policies_core.DEFAULT_INCOME_MEASURE == irs_soi.DEFAULT_INCOME_MEASURE
    assert (
        policies_core.INCOME_MEASURE_TAXABLE_INCOME
        == irs_soi.INCOME_MEASURE_TAXABLE_INCOME
    )
    assert policies_core.INCOME_MEASURE_AGI == irs_soi.INCOME_MEASURE_AGI
    # And the default is a member of the set, in both.
    for module in (policies_core, irs_soi):
        assert module.DEFAULT_INCOME_MEASURE in module.INCOME_MEASURES


def test_the_split_readers_default_is_the_named_constant():
    """Not a repeated literal: the signature default is the shared constant."""
    import inspect

    default = inspect.signature(
        IRSSOIData.get_filers_by_status_thresholds
    ).parameters["income_measure"].default
    assert default == irs_soi.DEFAULT_INCOME_MEASURE
    assert default in INCOME_MEASURES


# -- the loader ----------------------------------------------------------------


def test_the_pooled_reader_publishes_both_columns():
    info = IRSSOIData().get_filers_by_bracket(year=SOI_YEAR, threshold=20_000.0)
    assert info["avg_agi"] > info["avg_taxable_income"] > 0


def test_the_split_reader_refuses_an_unknown_measure():
    thresholds = dict.fromkeys(FILING_STATUSES, 100_000.0)
    with pytest.raises(ValueError, match="unknown income_measure"):
        IRSSOIData().get_filers_by_status_thresholds(
            year=SOI_YEAR, thresholds=thresholds, income_measure="magi"
        )


@pytest.mark.parametrize("measure", INCOME_MEASURES)
def test_a_uniform_split_threshold_reproduces_the_pooled_path(measure):
    """W7's byte-identity survives on the AGI column too.

    Table 1.1 supplies the level and Table 1.2 only the composition, for AGI
    exactly as for taxable income, so four statuses at one floor sum back to the
    pooled aggregate. Any movement is attributable to the per-status floors
    alone, on either column.
    """
    irs = IRSSOIData()
    threshold = 100_000.0
    pooled = irs.get_filers_by_bracket(year=SOI_YEAR, threshold=threshold)
    split = irs.get_filers_by_status_thresholds(
        year=SOI_YEAR,
        thresholds=dict.fromkeys(FILING_STATUSES, threshold),
        income_measure=measure,
    )

    avg = pooled["avg_agi"] if measure == "agi" else pooled["avg_taxable_income"]
    expected = max(0.0, avg - threshold) * pooled["num_filers"]
    assert split["marginal_income_dollars"] == pytest.approx(expected, rel=1e-9)
    assert split["income_measure"] == measure


def test_the_split_agi_ratio_is_not_the_pooled_one():
    """Composing a pooled ratio would miss both Option 46 rows.

    The AGI switch is applied inside the split - each status's own marginal AGI
    above its own floor - and the two ratios do not even move the same way at
    the two alternatives' floors.
    """
    irs = IRSSOIData()

    def split_ratio(threshold, joint):
        thresholds = dict.fromkeys(FILING_STATUSES, threshold)
        thresholds["joint"] = joint
        taxable = irs.get_filers_by_status_thresholds(
            year=SOI_YEAR, thresholds=thresholds, income_measure="taxable_income"
        )
        agi = irs.get_filers_by_status_thresholds(
            year=SOI_YEAR, thresholds=thresholds, income_measure="agi"
        )
        return agi["marginal_income_dollars"] / taxable["marginal_income_dollars"]

    def pooled_ratio(threshold):
        info = irs.get_filers_by_bracket(year=SOI_YEAR, threshold=threshold)
        return (info["avg_agi"] - threshold) / (info["avg_taxable_income"] - threshold)

    one_pp_split = split_ratio(20_000.0, 40_000.0)
    two_pp_split = split_ratio(100_000.0, 200_000.0)

    assert one_pp_split == pytest.approx(1.4052, abs=5e-4)
    assert two_pp_split == pytest.approx(1.2535, abs=5e-4)
    # Opposite directions against the pooled figure, which is the point.
    assert one_pp_split > pooled_ratio(20_000.0)
    assert two_pp_split < pooled_ratio(100_000.0)


# -- the scoring branches ------------------------------------------------------


def test_the_agi_base_prices_the_column_its_source_states():
    """Same returns, same floor, the other quantity."""
    irs = IRSSOIData()
    threshold = 2_000_000.0
    info = irs.get_filers_by_bracket(year=SOI_YEAR, threshold=threshold)
    ratio = (info["avg_agi"] - threshold) / (info["avg_taxable_income"] - threshold)

    taxable = _policy(
        affected_income_threshold=threshold,
        ordinary_income_base=False,
        data_year=SOI_YEAR,
    )
    agi = _policy(
        affected_income_threshold=threshold,
        ordinary_income_base=False,
        income_measure=INCOME_MEASURE_AGI,
        data_year=SOI_YEAR,
    )

    taxable_annual = taxable.estimate_static_revenue_effect(0.0, use_real_data=True)
    agi_annual = agi.estimate_static_revenue_effect(0.0, use_real_data=True)

    assert agi_annual == pytest.approx(taxable_annual * ratio, rel=1e-9)
    assert agi._soi_avg_agi_in_bracket == pytest.approx(info["avg_agi"])
    # The taxable-income field keeps meaning taxable income, so every other
    # reader of it - the shipped captions among them - stays correct.
    assert agi.avg_taxable_income_in_bracket == pytest.approx(
        info["avg_taxable_income"]
    )


def test_the_agi_annual_is_carried_rather_than_recomputed_the_other_way():
    """Years 2-10 fall out of the SOI branch and must not silently re-derive.

    Year one populates ``affected_taxpayers_millions``, so the second call takes
    the fallback branch, which reconstructs marginal income from
    ``avg_taxable_income_in_bracket`` - the other column. The cached annual is
    what stops that, and this fails the same way W7's split cache would.
    """
    policy = _policy(
        affected_income_threshold=2_000_000.0,
        ordinary_income_base=False,
        income_measure=INCOME_MEASURE_AGI,
        data_year=SOI_YEAR,
    )
    first = policy.estimate_static_revenue_effect(0.0, use_real_data=True)
    second = policy.estimate_static_revenue_effect(0.0, use_real_data=True)
    assert second == pytest.approx(first, rel=0, abs=0)


def test_a_caller_supplied_base_is_used_exactly_as_given():
    """An aggregate the caller supplied carries no SOI column to reclassify."""
    policy = _policy(
        annual_revenue_change_billions=42.0,
        ordinary_income_base=False,
        income_measure=INCOME_MEASURE_AGI,
    )
    assert policy.estimate_static_revenue_effect(0.0, use_real_data=True) == 42.0
    assert policy._soi_avg_agi_in_bracket is None


# -- the classification --------------------------------------------------------


def test_the_rule_names_exactly_three_records_and_each_carries_its_sentence():
    assert set(_AGI_BASE_POLICY_IDS) == {
        "cbo_opt46_agi_surtax_1pp_20k",
        "cbo_opt46_agi_surtax_2pp_100k",
        "warren_ultramillionaire_surtax_3pp",
        # Lane R3: CBO's 2022 volume, option 13 alternatives 3 and 4. Both state
        # the reform on AGI in as many words, which is the whole of
        # AGI_BASE_RULE's test.
        "cbo2023_opt13_agi_surtax_1pp_stdded",
        "cbo2023_opt13_agi_surtax_2pp_bracket4",
    }
    for policy_id, sentence in _AGI_BASE_POLICY_IDS.items():
        assert policy_id in KNOWN_SCORES, policy_id
        assert "AGI" in sentence, policy_id
    assert "in as many words" in AGI_BASE_RULE


def test_every_classified_record_is_agi_inclusive():
    """An AGI column implies the AGI-inclusive base; the record must agree."""
    for policy_id in _AGI_BASE_POLICY_IDS:
        assert KNOWN_SCORES[policy_id].agi_inclusive_base is True, policy_id


def test_the_three_agi_inclusive_records_left_alone_stay_on_taxable_income():
    """Held on their own sources' words, and the lane doc says what that costs.

    Two state taxable income in as many words; the third states wage and
    investment income, which is neither SOI column. All three would score
    *worse* on the AGI column, which is why the reason has to be the document.
    """
    for policy_id in (
        "medicare_surcharge_2pp",
        "illustrative_top_rate_5pp",
        "illustrative_500k_2pp",
    ):
        score = KNOWN_SCORES[policy_id]
        assert score.agi_inclusive_base is True
        assert agi_base_source_sentence(score) is None
        policy = create_policy_from_score(score)
        assert policy.income_measure == INCOME_MEASURE_TAXABLE_INCOME, policy_id


def test_every_ordinary_rate_record_takes_the_measure_its_record_declares():
    seen = 0
    for score in KNOWN_SCORES.values():
        if validation_shape(score) != "ordinary_rate":
            continue
        policy = create_policy_from_score(score)
        if policy is None:
            continue
        seen += 1
        expected = (
            INCOME_MEASURE_AGI
            if score.policy_id in _AGI_BASE_POLICY_IDS
            else INCOME_MEASURE_TAXABLE_INCOME
        )
        assert policy.income_measure == expected, score.policy_id
    assert seen >= len(_AGI_BASE_POLICY_IDS)


def test_forcing_the_ordinary_base_also_forces_the_ordinary_column():
    """``cold_holdout.py --ordinary-base`` asks what the ordinary treatment gives.

    Both branches of that diagnostic must remain constructible; an AGI column
    under a forced ordinary correction is the contradiction TaxPolicy refuses.
    """
    score = KNOWN_SCORES["cbo_opt46_agi_surtax_1pp_20k"]
    forced = create_policy_from_score(score, ordinary_income_base=True)
    assert forced.income_measure == INCOME_MEASURE_TAXABLE_INCOME
    left = create_policy_from_score(score, ordinary_income_base=False)
    assert left.income_measure == INCOME_MEASURE_AGI


# -- the preset surface --------------------------------------------------------


def test_a_preset_declaring_nothing_takes_the_shared_default():
    assert income_measure_for_preset(None) == DEFAULT_INCOME_MEASURE
    assert income_measure_for_preset({}) == DEFAULT_INCOME_MEASURE
    assert income_measure_for_preset({"agi_inclusive_base": True}) == (
        DEFAULT_INCOME_MEASURE
    )
    assert income_measure_for_preset({"income_measure": "agi"}) == INCOME_MEASURE_AGI


def test_a_preset_typo_is_refused_where_the_catalog_entry_is_still_in_hand():
    """A bad value must not wait until TaxPolicy construction to be caught.

    Left to ``__post_init__`` it would surface from six different call sites
    with no clue which preset carried it, and only on the surfaces that build a
    policy - the catalog itself would import clean.
    """
    with pytest.raises(ValueError, match="Warren Ultra-Millionaire Surtax"):
        income_measure_for_preset(
            {"income_measure": "AGI"}, preset_name="Warren Ultra-Millionaire Surtax"
        )
    with pytest.raises(ValueError, match="expected one of"):
        income_measure_for_preset({"income_measure": "adjusted_gross_income"})
    # The name is optional and its absence must not mask the error.
    with pytest.raises(ValueError, match="<unnamed>"):
        income_measure_for_preset({"income_measure": "magi"})


def test_every_catalog_entry_declares_a_measure_this_model_knows():
    """Walk the whole catalog by key, so a typo fails with its preset's name."""
    from fiscal_model.app_data import PRESET_POLICIES

    for name, entry in PRESET_POLICIES.items():
        measure = income_measure_for_preset(entry, preset_name=name)
        assert measure in INCOME_MEASURES, name


def test_only_the_warren_preset_declares_an_agi_column():
    """One preset, because one preset's source states AGI in as many words."""
    from fiscal_model.app_data import PRESET_POLICIES

    declaring = {
        name
        for name, entry in PRESET_POLICIES.items()
        if entry.get("income_measure") == "agi"
    }
    assert declaring == {"Warren Ultra-Millionaire Surtax"}

    # And the two other AGI-inclusive presets are deliberately not among them.
    for name in ("High-Earner Medicare Surcharge 2pp", "Progressive Millionaire Tax"):
        assert PRESET_POLICIES[name].get("agi_inclusive_base") is True
        assert income_measure_for_preset(PRESET_POLICIES[name]) == (
            INCOME_MEASURE_TAXABLE_INCOME
        )


def test_every_preset_construction_site_reads_the_same_answer():
    """H1's property, extended to the second attribute.

    The composer, the API's preset route, Tailor's preset seed and the three
    comparison tabs all build a preset's TaxPolicy. If one of them stops reading
    the measure, the app prints two numbers for one specification again.
    """
    import inspect

    from fiscal_model.composer import composer
    from fiscal_model.ui.tabs import multi_model, policy_comparison, side_by_side

    modules = [composer, multi_model, policy_comparison, side_by_side]
    for module in modules:
        source = inspect.getsource(module)
        assert "ordinary_income_base_for_preset(" in source, module.__name__
        assert "income_measure_for_preset(" in source, module.__name__


def test_the_warren_preset_is_scored_on_the_agi_column():
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.composer.composer import _build_preset_policy

    policy, _ = _build_preset_policy(
        "Warren Ultra-Millionaire Surtax",
        PRESET_POLICIES["Warren Ultra-Millionaire Surtax"],
    )
    assert policy.income_measure == INCOME_MEASURE_AGI
    assert policy.ordinary_income_base is False


# -- the caption ---------------------------------------------------------------


def test_the_caption_fires_only_where_the_column_moved_the_number():
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.composer.composer import _build_preset_policy, _scorer_for
    from fiscal_model.ui.tabs.results_summary import agi_income_column_caption

    moved_name = "Warren Ultra-Millionaire Surtax"
    policy, use_real = _build_preset_policy(moved_name, PRESET_POLICIES[moved_name])
    result = _scorer_for(policy, use_real).score_policy(policy, dynamic=False)
    caption = agi_income_column_caption(policy, result)
    assert "AGI itself" in caption
    assert "2,000,000" in caption

    held_name = "High-Earner Medicare Surcharge 2pp"
    held, use_real = _build_preset_policy(held_name, PRESET_POLICIES[held_name])
    held_result = _scorer_for(held, use_real).score_policy(held, dynamic=False)
    assert agi_income_column_caption(held, held_result) == ""


def test_the_caption_reconstructs_the_taxable_column_figure():
    """Computed, not stored: the ratio comes from the same SOI read.

    It undoes THIS change and nothing else, which is the convention every
    caption in that module follows.
    """
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.composer.composer import _build_preset_policy, _scorer_for
    from fiscal_model.ui.tabs.results_summary import agi_income_column_caption

    name = "Warren Ultra-Millionaire Surtax"
    entry = dict(PRESET_POLICIES[name])
    agi_policy, use_real = _build_preset_policy(name, entry)
    agi_total = sum(
        _scorer_for(agi_policy, use_real)
        .score_policy(agi_policy, dynamic=False)
        .final_deficit_effect
    )

    entry.pop("income_measure")
    taxable_policy, use_real = _build_preset_policy(name, entry)
    taxable_total = sum(
        _scorer_for(taxable_policy, use_real)
        .score_policy(taxable_policy, dynamic=False)
        .final_deficit_effect
    )

    result = _scorer_for(agi_policy, use_real).score_policy(agi_policy, dynamic=False)
    caption = agi_income_column_caption(agi_policy, result)
    assert f"\\${taxable_total:+,.1f}B" in caption
    assert f"\\${agi_total:+,.1f}B" in caption
