"""
What the pre-2025-law presets score against current law.

A score is a difference from a baseline. The site's baseline is CBO's
February 2026 Outlook (publication 61882), which already contains the July
2025 reconciliation law, P.L. 119-21. Nine presets were built for the
2024-25 question, "what does extending or repealing this cost against the law
as it stood before July 2025?", and carry ``pre_2025_law=True`` in
``fiscal_model.policy_status``. Their stored scores answer that question.

This module gives each of them the answer on the site's own baseline, one of
three kinds:

- ``already_law``: the reform is in current law, so the increment is $0.
  Where the enacted version is more generous than the preset (the CTC at
  $2,200 indexed, the estate exemption at $15M, the SALT cap at $40,000
  through 2029), the $0 is the extension having happened. The preset's own,
  less generous design would raise revenue against current law; that
  difference is named, not scored.
- ``same_as``: the current-law answer is another preset's score exactly.
  "Extend TCJA without the SALT cap" against a baseline that already contains
  TCJA is "repeal the SALT cap", and ``salt-cap-repeal`` is scored on the
  current-law cap path (``SaltCapBaseline.CURRENT_LAW``, PR #161).
- ``not_computed``: part of the reform is current law and the rest is not
  scored. The page says what is already gone, from a published table.

No score is computed here and no model code is read. Line references are to
JCT JCX-35-25, transcribed in
``data_files/validation/pl119_21_jct_line_items.csv``.

Lane: ``planning/lanes/BET1_law_baseline_switch.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from fiscal_model.policy_status import POLICY_STATUS_MAP

CurrentLawKind = Literal["already_law", "same_as", "not_computed"]

JCX_35_25 = "JCT JCX-35-25 (1 July 2025)"
JCX_35_25_URL = "https://www.jct.gov/publications/2025/jcx-35-25/"


@dataclass(frozen=True)
class CurrentLawAnswer:
    """One pre-2025-law preset's answer on the current-law baseline."""

    kind: CurrentLawKind
    reason: str
    source: str
    url: str
    #: For ``already_law``: always 0.0. For ``same_as`` and ``not_computed``: None
    #: (``same_as`` reads the named preset's stored score; ``not_computed`` has none).
    billions: float | None = None
    #: For ``same_as``: the preset id whose stored conventional score is the answer.
    same_as: str | None = None
    #: For ``not_computed``: the published size of the part already in current law,
    #: in this app's sign convention (positive adds to the deficit).
    already_ended_billions: float | None = None

    def to_export(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "billions": self.billions,
            "same_as": self.same_as,
            "already_ended_billions": self.already_ended_billions,
            "reason": self.reason,
            "source": self.source,
            "url": self.url,
        }


def _already(reason: str, source: str = JCX_35_25, url: str = JCX_35_25_URL) -> CurrentLawAnswer:
    return CurrentLawAnswer("already_law", reason, source, url, billions=0.0)


CURRENT_LAW_VIEW: dict[str, CurrentLawAnswer] = {
    "🏛️ TCJA Full Extension (CBO: $4.6T)": _already(
        "P.L. 119-21 made the individual TCJA provisions permanent (JCX-35-25 "
        "chapter 1, items 1-7), so they are in the baseline already. Current "
        "law is more generous than this preset on two pieces: the child tax "
        "credit is $2,200 and indexed, and the SALT cap is $40,000 through "
        "2029 before returning to $10,000. The preset's tighter versions "
        "would raise revenue against current law; that is not scored here."
    ),
    "🏛️ TCJA Rates Only": _already(
        "P.L. 119-21 made the TCJA rate schedule permanent (JCX-35-25 "
        "chapter 1, item 1)."
    ),
    "🏠 Estate Tax: Extend TCJA (CBO: $167B)": _already(
        "P.L. 119-21 set the estate and gift exemption at $15 million from "
        "2026, indexed (JCX-35-25 chapter 1, item 6). That is more generous "
        "than the TCJA exemption this preset extends; going back to the "
        "preset's level would raise revenue, which is not scored here."
    ),
    "👶 CTC Extension (CBO: $600B)": _already(
        "P.L. 119-21 made the child tax credit permanent at $2,200, indexed "
        "(JCX-35-25 chapter 1, item 4). That is more generous than the $2,000 "
        "this preset extends; cutting back to $2,000 would raise revenue, "
        "which is not scored here."
    ),
    "⚖️ AMT: Extend TCJA Relief ($1.36T)": _already(
        "P.L. 119-21 made the higher AMT exemptions permanent, with new "
        "phase-out thresholds (JCX-35-25 chapter 1, item 7)."
    ),
    "🌱 Repeal EV Credits (-$182B)": _already(
        "P.L. 119-21 ended the clean-vehicle credits (secs. 30D and 45W) for "
        "vehicles acquired after 30 September 2025 (JCX-35-25 chapter 5, "
        "items A.2 and A.3). There is nothing left to repeal."
    ),
    "🏛️ TCJA Extension (No SALT Cap)": CurrentLawAnswer(
        "same_as",
        "TCJA is already permanent, so on current law this proposal is a "
        "repeal of the SALT cap. That is the Repeal SALT Cap preset, which is "
        "scored against the current-law cap path: $40,000 rising 1% a year "
        "through 2029, then $10,000 (P.L. 119-21 sec. 70120). The figure is "
        "that preset's score.",
        "This model, on CBO's February 2026 baseline",
        "/explore/salt-cap-repeal",
        same_as="salt-cap-repeal",
    ),
    "🌱 Repeal IRA Clean Energy Credits (-$851B)": CurrentLawAnswer(
        "not_computed",
        "P.L. 119-21 already ended or cut back many of these credits. JCT "
        "puts those terminations at $542.7 billion of revenue over "
        "FY2025-2034 (JCX-35-25 chapter 5, subchapter A). Repealing what is "
        "left would save less than the full-repeal figure, but this model "
        "has not scored the remainder. Subtracting JCT's number from Tax "
        "Foundation's would mix two estimators, so it is not done here.",
        JCX_35_25,
        JCX_35_25_URL,
        already_ended_billions=-542.653,
    ),
}


def current_law_answer(label: str | None) -> CurrentLawAnswer | None:
    """The current-law answer for a pre-2025-law preset, or None."""
    if not label:
        return None
    return CURRENT_LAW_VIEW.get(label)


def pre_2025_labels() -> set[str]:
    return {label for label, status in POLICY_STATUS_MAP.items() if status.pre_2025_law}


__all__ = [
    "CURRENT_LAW_VIEW",
    "CurrentLawAnswer",
    "CurrentLawKind",
    "current_law_answer",
    "pre_2025_labels",
]
