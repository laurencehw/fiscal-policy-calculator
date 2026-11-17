"""
Three current-law yardsticks a score can be measured against.

CBO vintages (February 2024 / January 2025 / February 2026) are editions of
the Outlook. These three *law* baselines are the current-law alternatives
the 2026 tax debate actually uses:

- ``current`` — CBO's February 2026 baseline. It already includes P.L. 119-21
  (the July 2025 reconciliation law). This is the site default.
- ``pre2025`` — current law as it stood before P.L. 119-21: TCJA individual
  provisions and many IRA energy credits scheduled to expire. Closest published
  edition is CBO's January 2025 Outlook.
- ``extended`` — February 2026 current law, but with P.L. 119-21's
  *temporary* provisions made permanent. That is the live 2026 debate.

A score is a *difference from a baseline*, not a property of the policy
alone. Extending the TCJA individual cuts costs about $4.6 trillion against
pre-2025 law (they would otherwise expire) and about $0 against current law
(they are already permanent). The same arithmetic now applies to P.L. 119-21's
temporary cuts.

This module does not rescore presets. It names the yardstick, sources the
published difference between the yardsticks, and says how each Explore
preset should be *presented* on each one. Stored scores stay the February
2026 conventional path; presets that reconstruct a P.L. 119-21 question
are already labelled off that path by ``policy_status``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from fiscal_model.policy_status import POLICY_STATUS_MAP

LawId = Literal["current", "pre2025", "extended"]
PresetRole = Literal["live", "already_law", "remainder_unscored"]
PresentationKind = Literal[
    "live",
    "already_law",
    "remainder_unscored",
    "reconstruction",
    "current_law_score_on_other_yardstick",
]

LAW_IDS: tuple[LawId, ...] = ("current", "pre2025", "extended")
DEFAULT_LAW: LawId = "current"

# Presets whose modelled reform is already in February 2026 current law.
# Incremental score against ``current`` / ``extended`` is $0; the stored
# figure is the pre-enactment reconstruction, which is the right number
# against ``pre2025``. Enacted details differ on some of these (CTC $2,200
# vs this preset's $2,000; SALT $40,000 vs TCJA's $10,000 cap inside the
# full-extension bundle) — the $0 is the extension having happened, not a
# line-item identity with the statute.
ALREADY_LAW_PRESETS: frozenset[str] = frozenset(
    {
        "tcja-full-extension",
        "tcja-rates-only",
        "estate-extend-tcja",
        "amt-extend-tcja-relief",
        "ctc-extension",
        "ev-credit-repeal",
    }
)

# Part of the modelled reform is in current law, part is not. The stored
# figure is the pre-2025 reconstruction of the whole; the remainder against
# today's baseline is not computed in this PR.
REMAINDER_UNSCORED_PRESETS: frozenset[str] = frozenset(
    {
        "tcja-extension-no-salt-cap",
        "ira-clean-energy-repeal",
    }
)


@dataclass(frozen=True)
class SourcedFigure:
    """One published number that distinguishes two law baselines."""

    billions: float
    window: str
    convention: str
    source: str
    url: str
    approximated: bool = False
    note: str | None = None

    def to_export(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LawBaseline:
    id: LawId
    short_label: str
    title: str
    phrase: str
    summary: str
    lesson: str
    cbo_vintage: str | None
    versus_current: SourcedFigure | None

    def to_export(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["versus_current"] = (
            None if self.versus_current is None else self.versus_current.to_export()
        )
        return payload


# CBO, *Estimated Budgetary Effects of Public Law 119-21 … Relative to CBO's
# January 2025 Baseline*, publication 61570 (21 July 2025). Conventional
# unified-deficit effect of the enacted law; cost estimates of this kind
# exclude macroeconomic feedback and debt service.
PL119_21_CONVENTIONAL = SourcedFigure(
    billions=3400.0,
    window="FY2025-2034",
    convention="conventional unified deficit; excludes macroeconomic feedback and debt service",
    source="CBO publication 61570 (21 July 2025)",
    url="https://www.cbo.gov/publication/61570",
    note=(
        "As enacted 4 July 2025: −$1.1 trillion direct spending and −$4.5 "
        "trillion revenues, a $3.4 trillion net increase in the unified deficit."
    ),
)

# CBO, *The Budget and Economic Outlook: 2026 to 2036*, publication 62105
# (February 2026), Chapter 5 / Box 5-1. Same law, on the Outlook window,
# with debt service and then macroeconomic effects.
PL119_21_OUTLOOK = SourcedFigure(
    billions=4700.0,
    window="FY2026-2035",
    convention="unified deficit including macroeconomic effects and debt service",
    source="CBO publication 62105 (February 2026), Chapter 5",
    url="https://www.cbo.gov/publication/62105",
    note=(
        "Primary deficits +$3.7 trillion and debt service +$0.9 trillion over "
        "FY2026–2035, from the July 2025 cost estimate shifted onto this "
        "window; macroeconomic effects take the total to +$4.7 trillion. "
        "The conventional $3.4 trillion in publication 61570 is the same law "
        "on FY2025–2034 without those two channels."
    ),
)

# CRFB, 19 February 2026, reading CBO's February 2026 Outlook. This is not
# CBO's own table of "make the enacted temporary provisions permanent"; CBO
# has not published that table for the enacted law. Marked approximated
# because the window is eleven fiscal years (FY2026–2036) rather than the
# site's FY2026–2035, and because the figure is CRFB's, not CBO's.
TEMPS_EXTENDED_PRIMARY = SourcedFigure(
    billions=1900.0,
    window="FY2026-2036",
    convention="primary deficit; excludes debt service and macroeconomic effects",
    source="CRFB, 19 February 2026, off CBO's February 2026 baseline",
    url="https://www.crfb.org/blogs/debt-could-reach-131-gdp-under-alternative-scenario",
    approximated=True,
    note=(
        "CRFB: making temporary P.L. 119-21 provisions permanent adds $1.9 "
        "trillion to primary deficits through FY2036, including about $290 "
        "billion in FY2036. The site's scored window is FY2026–2035, so the "
        "ten-year increment is smaller by that last year and is not separately "
        "published. Tax pieces named: tips, overtime and the senior deduction "
        "expire after 2028; the $40,000 SALT cap after 2029; factory expensing "
        "is similarly time-limited. Spending pieces (defense and immigration "
        "appropriations through FY2029) are in the $1.9 trillion too."
    ),
)

# CBO/JCT letter to Sen. Merkley, 12 June 2025 (publication 61471). House-passed
# H.R. 1, not the enacted law — a related published estimate, kept so a reader
# can see CBO's own arithmetic of "make the temporary tax cuts permanent" on a
# package that is not P.L. 119-21 as enacted.
HOUSE_PASSED_TEMPS = SourcedFigure(
    billions=1400.0,
    window="FY2025-2034",
    convention="primary deficit, 16 tax provisions in House-passed H.R. 1",
    source="CBO publication 61471 (12 June 2025)",
    url="https://www.cbo.gov/publication/61471",
    approximated=True,
    note=(
        "House-passed H.R. 1, not P.L. 119-21 as enacted. Permanently enacting "
        "16 tax provisions that would sunset in 2028 or 2029 adds $1.4 trillion "
        "to primary deficits and $687 billion of debt service over FY2025–2034. "
        "Cited as CBO's published method for this kind of question, not as the "
        "score of the enacted temporary package."
    ),
)

_CURRENT_LESSON = (
    "A score is the difference from this baseline, not a property of the "
    "policy on its own. CBO's February 2026 Outlook already includes P.L. "
    "119-21, so extending the TCJA individual cuts — the 2024–25 debate — "
    "is already current law. Scoring that extension again here would count "
    "it twice. The live 2026 question is whether to extend the law's "
    "temporary pieces (tips, overtime, the $40,000 SALT cap, and others), "
    "which this baseline assumes expire on schedule."
)

_PRE2025_LESSON = (
    "Against this yardstick the TCJA individual cuts expire after 2025, "
    "as they were written before P.L. 119-21. Extending them is a large "
    "new cost — CBO scored a full extension around $4.6 trillion — because "
    "the baseline does not already contain it. That is why the same proposal "
    "that scores $0 against current law scores trillions here. Other "
    "proposals on this page still show the number computed on CBO's "
    "February 2026 baseline; a full re-score on January 2025 current law "
    "is not in this release, and those rows say so."
)

_EXTENDED_LESSON = (
    "Current law assumes P.L. 119-21's temporary provisions expire: no tax "
    "on tips, overtime and a larger senior deduction after 2028, the $40,000 "
    "SALT cap after 2029, time-limited factory expensing, and several "
    "appropriation boosts. Making those permanent is the same kind of "
    "question TCJA extension was in 2024–25, on today's yardstick. CRFB, "
    "reading CBO's February 2026 baseline, puts the primary-deficit cost "
    "at $1.9 trillion through FY2036 — an eleven-year window, and not a "
    "CBO table of the enacted package. Preset rows still show scores "
    "computed on current law; they have not been re-run on this scenario."
)

LAW_BASELINES: dict[LawId, LawBaseline] = {
    "current": LawBaseline(
        id="current",
        short_label="Current law",
        title="Current law (CBO February 2026)",
        phrase="CBO Feb 2026 baseline (current law)",
        summary="CBO's February 2026 baseline, which already includes P.L. 119-21.",
        lesson=_CURRENT_LESSON,
        cbo_vintage="February 2026",
        versus_current=None,
    ),
    "pre2025": LawBaseline(
        id="pre2025",
        short_label="Pre-2025 law",
        title="Pre-2025 law (TCJA/IRA expire)",
        phrase="pre-2025 law",
        summary=(
            "Current law as it stood before P.L. 119-21: TCJA individual "
            "provisions and many IRA energy credits expire on their old schedule."
        ),
        lesson=_PRE2025_LESSON,
        cbo_vintage="January 2025",
        versus_current=PL119_21_OUTLOOK,
    ),
    "extended": LawBaseline(
        id="extended",
        short_label="Temps extended",
        title="Current law, P.L. 119-21 temporary provisions extended",
        phrase="current law, P.L. 119-21 temps extended",
        summary=(
            "February 2026 current law, but with P.L. 119-21's temporary "
            "provisions made permanent — the live 2026 debate."
        ),
        lesson=_EXTENDED_LESSON,
        cbo_vintage=None,
        versus_current=TEMPS_EXTENDED_PRIMARY,
    ),
}

WORKED_EXAMPLE = (
    "Take TCJA full extension. Against pre-2025 law it adds about $4.6 "
    "trillion to the deficit, because the individual cuts would otherwise "
    "expire after 2025. Against current law the same proposal scores $0: "
    "P.L. 119-21 already made those cuts permanent, so scoring the "
    "extension again would double-count. The 2026 debate is the same "
    "shape on a new yardstick — whether to extend the *temporary* pieces "
    "of that law, which current law still assumes expire."
)


def parse_law(value: str | None) -> LawId:
    """Unknown or empty values fall back to current law."""
    text = (value or "").strip().lower()
    if text in LAW_IDS:
        return text  # type: ignore[return-value]
    return DEFAULT_LAW


def role_of(preset_id: str) -> PresetRole:
    if preset_id in ALREADY_LAW_PRESETS:
        return "already_law"
    if preset_id in REMAINDER_UNSCORED_PRESETS:
        return "remainder_unscored"
    return "live"


def present_preset(preset_id: str, law: LawId) -> dict[str, Any]:
    """How Explore should treat one preset on one law baseline.

    ``display_score`` is ``\"stored\"`` (use the exported conventional
    figure), ``0`` (incremental is zero), or ``null`` (do not print the
    stored figure as if it belonged on this yardstick).
    """
    law = parse_law(law)
    role = role_of(preset_id)
    baseline = LAW_BASELINES[law]
    if law == "pre2025":
        if role in ("already_law", "remainder_unscored"):
            return {
                "kind": "reconstruction",
                "role": role,
                "display_score": "stored",
                "show_published": True,
                "score_is_on_this_law": True,
                "identity_baseline": baseline.phrase,
                "explanation": (
                    "This score is the pre-enactment reconstruction, which is "
                    "the right number against pre-2025 law."
                ),
            }
        return {
            "kind": "current_law_score_on_other_yardstick",
            "role": role,
            "display_score": "stored",
            "show_published": True,
            "score_is_on_this_law": False,
            "identity_baseline": LAW_BASELINES["current"].phrase,
            "explanation": (
                "This proposal is still scored on CBO's February 2026 "
                "baseline (current law). A pre-2025-law re-score is not "
                "yet computed. The *level* of the two baselines differs by "
                "CBO's estimate of P.L. 119-21."
            ),
        }
    if law == "extended":
        if role == "already_law":
            return {
                "kind": "already_law",
                "role": role,
                "display_score": 0,
                "show_published": False,
                "score_is_on_this_law": True,
                "identity_baseline": baseline.phrase,
                "explanation": (
                    "Already current law, and still current law if the "
                    "temporary pieces are extended. The incremental score "
                    "is $0. The 2026 debate is about those temporary pieces, "
                    "not this extension. Switch to pre-2025 law to see the "
                    "reconstruction of this proposal as it was scored before "
                    "enactment."
                ),
            }
        if role == "remainder_unscored":
            return {
                "kind": "remainder_unscored",
                "role": role,
                "display_score": None,
                "show_published": False,
                "score_is_on_this_law": False,
                "identity_baseline": baseline.phrase,
                "explanation": (
                    "Part of this proposal is already current law. The "
                    "exported score is the pre-2025 reconstruction of the "
                    "whole; what remains against an extended current-law "
                    "baseline is not yet computed."
                ),
            }
        return {
            "kind": "current_law_score_on_other_yardstick",
            "role": role,
            "display_score": "stored",
            "show_published": True,
            "score_is_on_this_law": False,
            "identity_baseline": LAW_BASELINES["current"].phrase,
            "explanation": (
                "This proposal is scored on CBO's February 2026 current-law "
                "baseline, not on a baseline that extends P.L. 119-21's "
                "temporary provisions. A re-score on that scenario is not "
                "yet computed. CRFB puts the scenario's primary-deficit "
                "level about $1.9 trillion higher through FY2036."
            ),
        }
    # current law
    if role == "already_law":
        return {
            "kind": "already_law",
            "role": role,
            "display_score": 0,
            "show_published": False,
            "score_is_on_this_law": True,
            "identity_baseline": baseline.phrase,
            "explanation": (
                "Already current law. The incremental score against CBO's "
                "February 2026 baseline is $0 — scoring the extension again "
                "would double-count P.L. 119-21. Switch to pre-2025 law to "
                "see the reconstruction of this proposal as it was scored "
                "before enactment."
            ),
        }
    if role == "remainder_unscored":
        return {
            "kind": "remainder_unscored",
            "role": role,
            "display_score": None,
            "show_published": False,
            "score_is_on_this_law": False,
            "identity_baseline": baseline.phrase,
            "explanation": (
                "Part of this proposal is already current law. The exported "
                "score is the pre-2025 reconstruction of the whole; what "
                "remains against today's baseline is not yet computed. "
                "Switch to pre-2025 law to see that reconstruction."
            ),
        }
    return {
        "kind": "live",
        "role": role,
        "display_score": "stored",
        "show_published": True,
        "score_is_on_this_law": True,
        "identity_baseline": baseline.phrase,
        "explanation": None,
    }


def to_export() -> dict[str, Any]:
    """JSON the static site reads."""
    classified = sorted(ALREADY_LAW_PRESETS | REMAINDER_UNSCORED_PRESETS)
    return {
        "default": DEFAULT_LAW,
        "param": "law",
        "worked_example": WORKED_EXAMPLE,
        "laws": [LAW_BASELINES[law_id].to_export() for law_id in LAW_IDS],
        "preset_roles": {preset_id: role_of(preset_id) for preset_id in classified},
        "classified": {
            preset_id: {law_id: present_preset(preset_id, law_id) for law_id in LAW_IDS}
            for preset_id in classified
        },
        # Any live preset shares this presentation; the id is not read.
        "live": {law_id: present_preset("corporate-28pct", law_id) for law_id in LAW_IDS},
        "figures": {
            "pl119_21_conventional": PL119_21_CONVENTIONAL.to_export(),
            "pl119_21_outlook": PL119_21_OUTLOOK.to_export(),
            "temps_extended_primary": TEMPS_EXTENDED_PRIMARY.to_export(),
            "house_passed_temps": HOUSE_PASSED_TEMPS.to_export(),
        },
    }


def _assert_roles_match_policy_status() -> None:
    """Load-time check: off-current-baseline P.L. 119-21 presets are classified."""
    off = {
        preset_id
        for preset_id, status in POLICY_STATUS_MAP.items()
        if not status.on_current_baseline
    }
    classified = ALREADY_LAW_PRESETS | REMAINDER_UNSCORED_PRESETS
    missing = off - classified
    extra = classified - off
    if missing or extra:
        raise RuntimeError(
            f"law_baselines roles drifted from policy_status: missing={sorted(missing)} extra={sorted(extra)}"
        )


_assert_roles_match_policy_status()


__all__ = [
    "ALREADY_LAW_PRESETS",
    "DEFAULT_LAW",
    "HOUSE_PASSED_TEMPS",
    "LAW_BASELINES",
    "LAW_IDS",
    "PL119_21_CONVENTIONAL",
    "PL119_21_OUTLOOK",
    "REMAINDER_UNSCORED_PRESETS",
    "TEMPS_EXTENDED_PRIMARY",
    "WORKED_EXAMPLE",
    "LawBaseline",
    "LawId",
    "PresetRole",
    "SourcedFigure",
    "parse_law",
    "present_preset",
    "role_of",
    "to_export",
]
