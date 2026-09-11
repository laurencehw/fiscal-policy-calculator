"""The behavioural-offset sign contract, enforced across every policy class.

``fiscal_model/scoring_engine.py`` books a score as
``deficit_after = (static_spending - static_revenue) + behavioral`` and hands
``estimate_behavioral_offset`` the year's **static revenue** effect. So an
offset carrying the *same* sign as static **erodes** the revenue change in both
directions, and an offset carrying the *opposite* sign **magnifies** it.

Four modules were found breaking that contract before this file existed —
``trade.py`` (Wave 3 L8), ``payroll.py`` (Wave 5 A), ``corporate.py`` (Wave 5 B)
and ``tax_expenditures_core.py`` (Wave 4 3a) — **each by a lane that was reading
the file for another reason, and none by a test**. The sweep in
``planning/lanes/SWEEP_offset_sign.md`` found three more inverted modules and
four ``abs()`` ones. This file is what stops the eighth: it is parametrised over
every class that implements or inherits the offset, in both directions, and a
new module joins it the moment it is added to
``scripts/audit_offset_signs.build_cases``.

The sweep left one blanket exemption behind — the whole of
``TaxExpenditurePolicy``, which magnified unconditionally — and lane W7 closed
it by reading the sources reform by reform. ``CONVENTION_EXCEPTIONS`` is now a
set of **policies**, so an exemption is a claim about one reform with a
document behind it rather than a module nobody checks. The per-reform table and
its citations are pinned at the end of this file.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.scoring import FiscalPolicyScorer  # noqa: E402
from scripts.audit_offset_signs import PROBE, build_cases  # noqa: E402

#: Cases allowed to return an **opposite-signed** offset, each with the source
#: that says the behavioural response *raises revenue* for that reform, so the
#: offset is a second channel rather than a haircut on the first. Adding an
#: entry here is a deliberate act with a citation attached, not a way to quiet
#: a failure.
#:
#: **These are policies, not classes.** Until lane W7 the whole of
#: ``TaxExpenditurePolicy`` sat here, because the module magnified every
#: offset for every expenditure and every reform. W7 settled
#: ``planning/MODELING_IMPROVEMENT.md`` section 6.2 item 8 by reading the
#: sources reform by reform and found the class holds **both** kinds: four of
#: its nine reforms magnify on a document and five erode, so the class is no
#: longer exempt and its erode reforms are held to the contract like everything
#: else. The documents are enumerated in
#: ``fiscal_model/tax_expenditures_core.OFFSET_DIRECTIONS`` and in
#: ``planning/lanes/W7_expenditure_offset_convention.md`` section 4.
#:
#: ``TaxExpenditurePolicy [SALT]`` -- CBO, extended discussion of Option 49
#: (``cbo.gov/budget-options/58635``), second alternative, which is this exact
#: reform: filers who keep itemising "would also choose to reduce their
#: spending on other deductible items… That reduction would further decrease
#: their itemized deductions and **increase their tax liability**." The
#: ``expand`` direction is the mirror, priced by Yale Budget Lab's
#: *Mortgage Interest Deduction: Options for Reform* -- raising the SALT limit
#: brings in new itemisers who then deduct mortgage interest too, taking that
#: expenditure from $323B to $497B, so the loss exceeds the SALT figure alone.
#:
#: The employer-health cap and the charitable benefit-rate ceiling are magnify
#: on their own documents too (CBO 60557 Option 56; CBO 58635's third
#: alternative), but the audit's SALT case is the only expenditure case built
#: in a magnify configuration, so it is the only label here.
CONVENTION_EXCEPTIONS: frozenset[str] = frozenset({"TaxExpenditurePolicy [SALT]"})


def _class_name(label: str) -> str:
    """``"CorporateTaxPolicy [reported]"`` -> ``"CorporateTaxPolicy"``."""
    return label.split(" [")[0]


@pytest.fixture(scope="module")
def scorer() -> FiscalPolicyScorer:
    return FiscalPolicyScorer()


def _cases_by_direction():
    for case in build_cases():
        for direction, builder in (
            ("increase", case.build_increase),
            ("cut", case.build_cut),
        ):
            if builder is None:
                continue
            yield pytest.param(case, direction, id=f"{case.label}-{direction}")


CASES = list(_cases_by_direction())


@pytest.mark.parametrize(("case", "direction"), CASES)
@pytest.mark.parametrize("probe", [PROBE, -PROBE], ids=["static+", "static-"])
def test_offset_carries_the_static_effect_sign(case, direction, probe):
    """The offset erodes, in both directions, unless a source says otherwise.

    **Every instance is probed with a positive and a negative static**, not
    only with the sign its own configuration produces. That is the whole point:
    an ``abs()`` the module's factories only ever feed positive statics is still
    an ``abs()``, and Tailor, the composer and ``bill_tracker/auto_scorer.py``
    are not bound by the factories. ``IRSEnforcementPolicy`` is exactly that
    case — it clamps a funding cut's static to ``0.0``, so its ``abs()`` was
    unreachable through its own constructor and a check that probed only the
    reachable direction passed while the rule was wrong.
    """
    builder = case.build_increase if direction == "increase" else case.build_cut
    policy = builder()
    if case.classify_from == "score":
        pytest.skip(
            f"{case.label} does not read static_effect — it rebuilds the "
            "response from its own brackets, so it has no function-level sign "
            "rule; the window check below is what covers it"
        )
    offset = float(policy.estimate_behavioral_offset(probe))

    if offset == 0.0:
        return  # a module that books no behavioural response keeps no sign

    same_sign = (offset > 0.0) == (probe > 0.0)
    if case.label in CONVENTION_EXCEPTIONS:
        assert not same_sign, (
            f"{case.label} is registered in CONVENTION_EXCEPTIONS as an "
            "opposite-signed convention but now returns a same-signed offset. "
            "If the convention was deliberately dropped, drop the exception too."
        )
        return

    assert same_sign, (
        f"{case.label} returns {offset:+.3f} against a static of {probe:+.1f}: "
        "an opposite-signed offset MAGNIFIES the score where the engine's "
        "deficit = -revenue + behavioural means it should erode it. Sign it "
        "with math.copysign, or register the class in CONVENTION_EXCEPTIONS "
        "with the source that says the response raises revenue both ways."
    )


@pytest.mark.parametrize(("case", "direction"), CASES)
def test_final_effect_does_not_exceed_the_static_effect(case, direction, scorer):
    """``|final| <= |static|`` end to end, over the whole scoring window.

    This is the sign contract's consequence in the quantity a user sees. It
    also catches a same-signed offset large enough to flip the score, which the
    function-level check above cannot see.
    """
    builder = case.build_increase if direction == "increase" else case.build_cut
    policy = builder()
    result = scorer.score_policy(policy, dynamic=False, include_uncertainty=False)
    static = float(np.sum(result.static_deficit_effect))
    final = float(np.sum(result.final_deficit_effect))

    if case.label in CONVENTION_EXCEPTIONS:
        pytest.skip(
            f"{case.label} magnifies by a documented convention; see "
            "CONVENTION_EXCEPTIONS in this file"
        )

    assert abs(final) <= abs(static) + 1e-6, (
        f"{case.label} ({direction}): |final| ${abs(final):,.1f}B exceeds "
        f"|static| ${abs(static):,.1f}B. The behavioural response is supposed "
        "to erode the static effect, not add to it."
    )


def test_convention_exceptions_are_exactly_the_documented_set():
    """One exception, and a new one has to be added on purpose.

    The set is the whole reason this file can be trusted: without it, the way
    to make a failing module pass is to add it here, and that has to be a
    visible, cited act rather than a quiet one.

    Since lane W7 it holds a **policy**, not a class. That is the difference
    between "this module is exempt" and "this reform has a document", and only
    the second is a claim anyone can check.
    """
    assert CONVENTION_EXCEPTIONS == frozenset({"TaxExpenditurePolicy [SALT]"})


def test_no_whole_class_is_exempt_from_the_contract():
    """An exception names a case, and every class has at least one case held.

    ``TaxExpenditurePolicy`` was a blanket exception until W7 — every reform it
    could express magnified, and the contract test could say nothing about any
    of them. It now has two cases with opposite tags, which is what makes the
    exemption a statement about one reform instead of about a module.
    """
    labels = [case.label for case in build_cases()]
    for class_name in {_class_name(label) for label in labels}:
        of_this_class = {label for label in labels if _class_name(label) == class_name}
        assert of_this_class - CONVENTION_EXCEPTIONS, (
            f"every case of {class_name} is in CONVENTION_EXCEPTIONS, so the "
            "contract is checked for none of them. An exception is for a "
            "reform with a source, not for a module."
        )


def test_every_offset_implementation_is_covered():
    """Every class defining the method appears in the case list.

    Adding a module with a behavioural offset and forgetting to sweep it is how
    all four of the found defects got in. This fails the moment that happens
    again.
    """
    import re

    defined: set[str] = set()
    for path in sorted((PROJECT_ROOT / "fiscal_model").glob("*.py")):
        source = path.read_text(encoding="utf-8", errors="replace")
        current: str | None = None
        for line in source.splitlines():
            match = re.match(r"class (\w+)\b", line)
            if match:
                current = match.group(1)
            if "def estimate_behavioral_offset" in line and current:
                defined.add(current)

    covered = {_class_name(case.label) for case in build_cases()}
    missing = defined - covered
    assert not missing, (
        f"{sorted(missing)} implement estimate_behavioral_offset but are not in "
        "scripts/audit_offset_signs.build_cases, so the sign contract is not "
        "being checked for them. Add a Case with a revenue increase and a "
        "revenue cut."
    )


# ---------------------------------------------------------------------------
# Decision 6 - the two shipped headlines that moved ship with a caption
# ---------------------------------------------------------------------------


def test_the_caption_fires_on_exactly_the_two_presets_that_moved(scorer):
    """One shipped preset still carries this caption; the other changed hands.

    Two of the 53 presets moved when the offsets were signed: ``Trump Corporate
    15%`` fell about 22% and ``Repeal ACA Premium Credits`` about 18%, and
    Decision 6 says a moved shipped number ships with its explanation rather
    than in silence.

    **``Trump Corporate 15%`` left this caption on 2026-09-11 and the reason is
    not that its explanation was dropped.** ``_offset_sign_changed`` fires for a
    ``CorporateTaxPolicy`` only in ``reported`` mode, because the ``abs()``
    defect PR #119 corrected lived in that branch alone - Wave 5 B had already
    signed ``derived``. Lane R5 flipped ``CORPORATE_APP_MODE`` to ``derived``,
    so the app no longer serves the number that defect produced, and there is no
    sign correction left to explain on that path. What the preset carries
    instead is ``corporate_mode_flip_caption``, asserted below, which names the
    figure the old default would have printed. The other 51 score to the cent
    what they scored before, so this caption must stay silent on them - a note
    that appears everywhere explains nothing.
    """
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.preset_handler import create_policy_from_preset
    from fiscal_model.ui.tabs.results_summary import behavioural_sign_caption

    captioned = []
    for label, data in PRESET_POLICIES.items():
        policy = create_policy_from_preset(data)
        if policy is None:
            continue
        result = scorer.score_policy(policy, dynamic=False, include_uncertainty=False)
        if behavioural_sign_caption(policy, result):
            captioned.append(label)

    assert len(captioned) == 1, captioned
    assert any("Repeal ACA Premium Credits" in label for label in captioned)
    assert not any("Trump Corporate 15" in label for label in captioned)

    # ...and the preset that left is covered by the caption that replaced it,
    # so no shipped figure moved twice and went unexplained once.
    from fiscal_model.ui.tabs.results_summary import corporate_mode_flip_caption

    label = next(lbl for lbl in PRESET_POLICIES if "Trump Corporate 15" in lbl)
    policy = create_policy_from_preset(PRESET_POLICIES[label])
    result = scorer.score_policy(policy, dynamic=False, include_uncertainty=False)
    assert corporate_mode_flip_caption(policy, result)


def test_the_caption_carries_the_scored_figures_and_the_old_headline(scorer):
    """Computed from the result, so it cannot drift from the number above it."""
    import numpy as np

    from fiscal_model.corporate import (
        CORPORATE_MODE_REPORTED,
        create_republican_corporate_cut,
    )
    from fiscal_model.ui.tabs.results_summary import behavioural_sign_caption

    # Explicitly ``reported``: this caption is about that branch's defect, and
    # since 2026-09-11 the factory's default is ``derived``, where it never
    # applied.
    policy = create_republican_corporate_cut(mode=CORPORATE_MODE_REPORTED)
    result = scorer.score_policy(policy, dynamic=False, include_uncertainty=False)
    note = behavioural_sign_caption(policy, result)

    static = float(np.sum(result.static_deficit_effect))
    behavioural = float(np.sum(result.behavioral_offset))
    assert f"{abs(behavioural):,.1f}B" in note
    assert f"{static:+,.1f}B" in note
    assert f"{static + behavioural:+,.1f}B" in note
    # The figure the headline would have carried before the sweep.
    assert f"{static - behavioural:+,.1f}B" in note
    assert "No elasticity changed" in note


def test_the_caption_stays_silent_on_a_rate_increase(scorer):
    """An ``abs()`` and the signed rule agree whenever the static is positive.

    Corporate's defect only ever bit a rate *cut*, so ``biden_corporate_28``
    scores exactly what it scored before and has nothing to explain.
    """
    from fiscal_model.corporate import create_biden_corporate_rate_only
    from fiscal_model.ui.tabs.results_summary import behavioural_sign_caption

    policy = create_biden_corporate_rate_only()
    result = scorer.score_policy(policy, dynamic=False, include_uncertainty=False)
    assert behavioural_sign_caption(policy, result) == ""


# ---------------------------------------------------------------------------
# The two rows the sweep moved report as reconstructions, not calibrations
# ---------------------------------------------------------------------------

#: The rows whose fitted constant reproduced its target only through the sign
#: defect this lane corrected. Both were reclassified rather than retuned, on
#: the precedent ``readiness.py`` cites and that Wave 2 L1 set for
#: ``pwbm_39_with_stepup`` and Wave 3 L8 for the two tariff rows.
RECLASSIFIED_BY_THE_SWEEP = ("trump_corporate_15", "repeal_ptc")


def test_the_two_moved_rows_report_as_unfitted_reconstructions():
    """Reclassify, do not retune, do not exempt.

    A constant fitted so that *static x (1 + offset share)* lands on a target
    is not a calibration to that target once the offset is signed - it was
    fitted to the defect. Both rows therefore report in the
    unfitted-reconstruction tier, where a documented miss is a finding about
    the module rather than a calibration regression, and both carry a
    ``known_limitations`` note saying so. Readiness requires the note: a Poor
    row *without* one is a hard failure rather than a warning.
    """
    from fiscal_model.validation import compute_scorecard

    entries = {e.policy_id: e for e in compute_scorecard().entries}
    for policy_id in RECLASSIFIED_BY_THE_SWEEP:
        entry = entries[policy_id]
        assert entry.calibrated_to_target is False, policy_id
        assert entry.known_limitations, policy_id
        joined = " ".join(entry.known_limitations).lower()
        assert "retuned" in joined, policy_id
        assert "provenance pass" in joined, policy_id


def test_no_other_row_left_the_fitted_tier():
    """The reclassification is two rows, named, and nothing else.

    ``calibrated_to_target`` is threaded through the corporate and PTC runners
    with a default of ``True``, so a scenario that says nothing keeps its tier.
    This fails if that default ever inverts and quietly empties the fitted tier.

    Every movement since has had to come through this assertion. On 2026-09-09
    lane H9 moved five more rows out - `ss_donut_250k`, `tcja_rates_only`,
    `eliminate_estate_tax`, `repeal_ira_credits` and `eliminate_mortgage`, each
    because the ledger revised its target and a constant fitted to a superseded
    figure is not fitted to its replacement. That is the ledger's own
    mechanism, not a default inverting, and it is why the counts below read
    16/39 where they read 21/34.

    On 2026-09-11 lane H7 moved a sixth, `cap_charitable`, on PR #119's rule
    rather than the ledger's: its annual reproduced -$200.0B only through an
    unsourced 0.40 behavioural magnitude, and H7 derived that magnitude from
    CRS R40518's central price elasticity of giving. A constant fitted through
    a magnitude a later lane sourced is not a calibration to the target either,
    so the counts read 15/40. `calibrated_to_target` is now threaded through
    the expenditure runner as well, with the same `True` default.
    """
    from fiscal_model.validation import GENERIC_CATEGORY, compute_scorecard

    summary = compute_scorecard()
    # The same split ``scripts/cold_holdout.py`` makes: the Generic category is
    # the out-of-sample tier and is neither of these two.
    specialized = [e for e in summary.entries if e.category != GENERIC_CATEGORY]
    fitted = [e for e in specialized if e.calibrated_to_target]
    reconstructions = [e for e in specialized if not e.calibrated_to_target]
    assert len(fitted) == 15, [e.policy_id for e in fitted]
    # 40 since 2026-09-11. It was 34 from 2026-09-05, when the corporate/PTC
    # provenance lane registered the FY2022 Green Book's rate-only row as a
    # second published corporate benchmark, unfitted by construction; H9's
    # five revised rows are the five that joined it.
    assert len(reconstructions) == 40, len(reconstructions)
    # And every row that left is named, so "the tier shrank" can never be a diff
    # nobody had to explain.
    moved_by_h9 = {
        "eliminate_estate_tax",
        "eliminate_mortgage",
        "repeal_ira_credits",
        "ss_donut_250k",
        "tcja_rates_only",
    }
    reconstruction_ids = {e.policy_id for e in reconstructions}
    assert moved_by_h9 <= reconstruction_ids
    assert "cap_charitable" in reconstruction_ids
    assert not (moved_by_h9 & {e.policy_id for e in fitted})


def test_strict_readiness_reports_no_fitted_tier_regression():
    """What the CI job actually checks, as a test rather than a CI log.

    A *fitted* benchmark rated Poor is strict-blocking, because its parameters
    exist to reproduce that target. Signing the corporate offset made
    ``trump_corporate_15`` exactly that, and the fix is the classification, not
    the constant and not an exemption. The runtime check is expected to fail
    locally on Python 3.14 and to pass on CI's 3.12; it is not this lane's.
    """
    from fiscal_model.readiness import build_readiness_report, strict_readiness_issues

    report = build_readiness_report()
    issues = strict_readiness_issues(report)
    offenders = [
        policy_id
        for issue in issues
        for policy_id in (issue.details.get("documented_calibrated_policy_ids") or [])
    ]
    assert not offenders, offenders
    assert all(issue.name == "runtime" for issue in issues), [i.name for i in issues]


# ---------------------------------------------------------------------------
# Lane W7 — the expenditure module's direction is per reform, and sourced
# ---------------------------------------------------------------------------

#: Every reform the tax-expenditure module can express through a shipped
#: factory, with the direction lane W7 read off a document. ``magnify`` means a
#: source says the behavioural response *raises* revenue for that reform;
#: ``erode`` is the engine's contract and the default. The inventory and its
#: quotations are in
#: ``planning/lanes/W7_expenditure_offset_convention.md`` section 4.
W7_EXPECTED_DIRECTIONS = (
    ("create_cap_employer_health_exclusion", "magnify", "CBO 60557 Option 56"),
    ("create_cap_charitable_deduction", "magnify", "CBO 58635 alt 3"),
    ("create_eliminate_salt_deduction", "magnify", "CBO 58635 alt 2"),
    ("create_repeal_salt_cap", "magnify", "the mirror of alt 2; Yale prices it"),
    ("create_eliminate_mortgage_deduction", "erode", "Poterba & Sinai WP 14253"),
    ("create_eliminate_step_up_basis", "erode", "CBO budget-options/54792"),
    ("create_cap_retirement_contributions", "erode", "CBO 2018/54799; default"),
    ("create_eliminate_like_kind_exchange", "erode", "no source found; default"),
)


@pytest.mark.parametrize(
    ("factory_name", "expected", "why"),
    W7_EXPECTED_DIRECTIONS,
    ids=[row[0] for row in W7_EXPECTED_DIRECTIONS],
)
def test_every_shipped_expenditure_reform_has_the_direction_its_source_states(
    factory_name, expected, why
):
    """The inventory, as a test rather than only as a lane doc.

    Four magnify and four erode, which is the whole of W7's finding: the
    module's old blanket convention was directionally right on some of its own
    benchmarks and wrong on others, and only reading the reforms one at a time
    could tell which.
    """
    from fiscal_model import tax_expenditures_factory as factories

    policy = getattr(factories, factory_name)()
    assert policy.resolved_offset_direction().value == expected, why


def test_an_unlisted_reform_erodes():
    """The default is the contract, not the convention.

    Absence of a statement is not evidence that the response raises revenue, so
    a reform with no entry in the table gets the same treatment as every other
    policy class in the repository.
    """
    from fiscal_model.policies import PolicyType
    from fiscal_model.tax_expenditures_core import (
        OFFSET_DIRECTIONS,
        OffsetDirection,
        TaxExpenditurePolicy,
        TaxExpenditureType,
    )

    policy = TaxExpenditurePolicy(
        name="Phase out the capital gains preference",
        description="a reform no document in the table covers",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.CAPITAL_GAINS,
        action="phase_out",
    )
    assert (policy.expenditure_type, "phase_out") not in OFFSET_DIRECTIONS
    assert policy.resolved_offset_direction() is OffsetDirection.ERODE
    assert policy.estimate_behavioral_offset(100.0) > 0
    assert policy.estimate_behavioral_offset(-100.0) < 0


def test_a_charitable_dollar_cap_does_not_inherit_the_rate_caps_verdict():
    """CBO gives one deduction two verdicts, and the table has to keep them apart.

    Capping the *value* of the charitable deduction raises revenue
    behaviourally — "an effect that would increase tax revenues" (CBO 58635,
    third alternative). Putting a *floor* under it loses revenue — "Those
    responses make the estimated increase in revenues under either alternative
    smaller than it would be otherwise" (CBO budget-options/54790) — because a
    floor can be bunched over and a rate ceiling cannot. So the magnify rule is
    scoped to ``BENEFIT_RATE`` and any other design falls back to erode rather
    than inheriting a verdict its document never gave.
    """
    from fiscal_model.policies import PolicyType
    from fiscal_model.tax_expenditures_core import (
        CapUnit,
        OffsetDirection,
        TaxExpenditurePolicy,
        TaxExpenditureType,
    )

    rate_cap = TaxExpenditurePolicy(
        name="Cap charitable deduction at 28%",
        description="benefit-rate ceiling",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.CHARITABLE,
        action="cap",
        cap_rate=0.28,
        cap_unit=CapUnit.BENEFIT_RATE,
    )
    dollar_cap = TaxExpenditurePolicy(
        name="Cap deductible contributions at $10,000",
        description="a dollar cap on the base, which no document scores this way",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.CHARITABLE,
        action="cap",
        cap_amount=10_000.0,
        cap_unit=CapUnit.BASE_DOLLARS,
    )

    assert rate_cap.resolved_offset_direction() is OffsetDirection.MAGNIFY
    assert dollar_cap.resolved_offset_direction() is OffsetDirection.ERODE


def test_every_magnify_entry_carries_a_source():
    """A direction that adds to a score has to name the sentence that allows it.

    The same discipline ``CONVENTION_EXCEPTIONS`` enforces one level up: the way
    to make a reform magnify must be to find a document, never to add a key.
    """
    from fiscal_model.tax_expenditures_core import OFFSET_DIRECTIONS, OffsetDirection

    for key, rule in OFFSET_DIRECTIONS.items():
        if rule.direction is not OffsetDirection.MAGNIFY:
            continue
        assert len(rule.source) > 120, key
        assert any(mark in rule.source for mark in ("CBO", "JCT", "Yale")), key


def test_an_explicit_direction_overrides_the_table():
    """Tailor and the composer are not bound by the table.

    The table records documents that have been read, not reforms that are
    allowed, so a caller who knows a direction can state it without editing it.
    """
    from fiscal_model.policies import PolicyType
    from fiscal_model.tax_expenditures_core import (
        OffsetDirection,
        TaxExpenditurePolicy,
        TaxExpenditureType,
    )

    policy = TaxExpenditurePolicy(
        name="Eliminate mortgage interest deduction",
        description="stated direction, against the table's default",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.MORTGAGE_INTEREST,
        action="eliminate",
        offset_direction=OffsetDirection.MAGNIFY,
    )
    assert policy.resolved_offset_direction() is OffsetDirection.MAGNIFY
    assert policy.estimate_behavioral_offset(100.0) < 0
