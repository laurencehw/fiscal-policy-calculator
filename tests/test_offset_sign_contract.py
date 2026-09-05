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

#: Classes allowed to return an **opposite-signed** offset, each with the
#: source that says the behavioural response moves revenue the same way in both
#: directions, so the offset is a second channel rather than a haircut on the
#: first. Adding an entry here is a deliberate act with a citation attached, not
#: a way to quiet a failure.
#:
#: ``TaxExpenditurePolicy`` -- CBO, *Options for Reducing the Deficit: 2025 to
#: 2034* (pub. 60557), Option 56. Capping the employer-health exclusion makes
#: employers offer less generous coverage **and** shifts compensation back into
#: taxable wages, and CBO's text has both channels increasing revenue. Worth
#: about +20% on that option and directionally right there; unsourced in
#: magnitude on every other expenditure benchmark. Choosing the convention
#: module-wide moves every fitted expenditure row and the whole leave-one-out
#: column together, so it is an owner decision, carried as item 8 of
#: ``planning/MODELING_IMPROVEMENT.md`` section 6.2.
CONVENTION_EXCEPTIONS: frozenset[str] = frozenset({"TaxExpenditurePolicy"})


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
    if _class_name(case.label) in CONVENTION_EXCEPTIONS:
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

    if _class_name(case.label) in CONVENTION_EXCEPTIONS:
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
    """
    assert CONVENTION_EXCEPTIONS == frozenset({"TaxExpenditurePolicy"})


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
    """Two of the 53 shipped presets moved when the offsets were signed.

    ``Trump Corporate 15%`` fell about 22% and ``Repeal ACA Premium Credits``
    about 18%, and Decision 6 says a moved shipped number ships with its
    explanation rather than in silence. The other 51 score to the cent what
    they scored before, so the caption must stay silent on them - a note that
    appears everywhere explains nothing.
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

    assert len(captioned) == 2, captioned
    assert any("Trump Corporate 15" in label for label in captioned)
    assert any("Repeal ACA Premium Credits" in label for label in captioned)


def test_the_caption_carries_the_scored_figures_and_the_old_headline(scorer):
    """Computed from the result, so it cannot drift from the number above it."""
    import numpy as np

    from fiscal_model.corporate import create_republican_corporate_cut
    from fiscal_model.ui.tabs.results_summary import behavioural_sign_caption

    policy = create_republican_corporate_cut()
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
