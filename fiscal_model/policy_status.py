"""
Curated legal status for preset policies ("date the law, not just the data").

Every preset models a policy question that was live on some date; several
have since been enacted, superseded, or partially overtaken by events —
most importantly the July 2025 budget-reconciliation law (H.R. 1, the
"One Big Beautiful Bill Act", P.L. 119-21), which extended the individual
TCJA provisions the flagship presets score as open questions.

The map below is hand-curated and keyed by stable preset id. Only presets
whose status is known with confidence carry an entry; everything else
renders no chip rather than a guessed one. Notes say what happened and
where the preset's score stands relative to it, not the new law's
parameters. Nothing here rescores a preset.

Statuses:
- ``proposed``      — put forward (bill, Green Book, campaign, options
                      analysis) but not enacted.
- ``enacted``       — became law substantially as modeled.
- ``superseded``    — the question the preset scores was overtaken by a
                      later law; the score is a pre-enactment reconstruction.
- ``partially``     — related measures were enacted, but not the schedule
                      the preset models.

``on_current_baseline`` is False when the *score* is still a pre-2025-law
reconstruction. CBO's February 2026 baseline already includes P.L. 119-21,
so labelling those figures "CBO Feb 2026 baseline" would claim the wrong
yardstick. Explore's law switch (``fiscal_model.law_baselines``) presents
those reconstructions against pre-2025 law and explains them as already
current law (or as a remainder not yet scored) on the other two yardsticks.
Repeal of the SALT cap is superseded as a legal question but its score was
moved onto current law (PR #161), so it stays True.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

STATUS_AS_OF = "2026-11-17"

PRE_2025_SCORE_SENTENCE = (
    "This score is relative to pre-2025 law, not CBO's February 2026 baseline, "
    "which already includes P.L. 119-21."
)

_OBBBA = "P.L. 119-21"

_OBBBA_NOTE = (
    "Individual TCJA provisions were extended by the July 2025 "
    "reconciliation law (H.R. 1, P.L. 119-21). This preset reconstructs "
    "the pre-enactment official score of extension as then proposed."
)

_GREEN_BOOK_NOTE = (
    "FY2025 Treasury Green Book proposal (Biden administration); "
    "not enacted."
)

_SS_OPTION_NOTE = (
    "Social Security solvency option from SSA/CBO options analyses; "
    "not enacted."
)


@dataclass(frozen=True)
class PolicyStatus:
    status: str  # "proposed" | "enacted" | "superseded" | "partially"
    note: str
    on_current_baseline: bool = True
    law: str | None = None

    @property
    def label(self) -> str:
        if self.law and self.status == "superseded":
            return f"Superseded by {self.law}"
        if self.law and self.status == "partially":
            return f"Partly overtaken by {self.law}"
        return {
            "proposed": "Proposed — not enacted",
            "enacted": "Enacted",
            "superseded": "Superseded by later law",
            "partially": "Partially overtaken by later law",
        }.get(self.status, self.status)

    @property
    def badge(self) -> str:
        return self.label

    @property
    def icon(self) -> str:
        return {
            "proposed": "🔵",
            "enacted": "🟢",
            "superseded": "🟠",
            "partially": "🟡",
        }.get(self.status, "⚪")

    def to_export(self) -> dict[str, Any]:
        """JSON the static site reads. ``baseline_sentence`` is the one
        sentence Explore prints; ``note`` keeps the provision-level why."""
        return {
            "status": self.status,
            "badge": self.badge,
            "note": self.note,
            "on_current_baseline": self.on_current_baseline,
            "baseline_sentence": (
                None if self.on_current_baseline else PRE_2025_SCORE_SENTENCE
            ),
        }


# Verified against JCX-35-25 (the Title VII text enacted as P.L. 119-21):
# rates, standard deduction, CTC, QBI, estate/gift exemption and AMT
# exemption were extended (some with enhancements); SALT was raised to
# $40,000 rather than repealed; clean-vehicle credits were terminated;
# IRA energy credits were terminated in part, not as a full repeal.
POLICY_STATUS_MAP: dict[str, PolicyStatus] = {
    # ── TCJA-extension family: overtaken by the July 2025 law ────────────
    "tcja-full-extension": PolicyStatus(
        "superseded", _OBBBA_NOTE, on_current_baseline=False, law=_OBBBA
    ),
    "tcja-extension-no-salt-cap": PolicyStatus(
        "superseded",
        _OBBBA_NOTE + " The July 2025 law also modified the SALT cap, so the "
        "no-cap variant modeled here differs from what was enacted.",
        on_current_baseline=False,
        law=_OBBBA,
    ),
    "tcja-rates-only": PolicyStatus(
        "superseded", _OBBBA_NOTE, on_current_baseline=False, law=_OBBBA
    ),
    "estate-extend-tcja": PolicyStatus(
        "superseded", _OBBBA_NOTE, on_current_baseline=False, law=_OBBBA
    ),
    "ctc-extension": PolicyStatus(
        "superseded",
        "P.L. 119-21 extended and enhanced the child tax credit ($2,200, "
        "indexed). This preset reconstructs extension of the $2,000 TCJA "
        "credit as then proposed.",
        on_current_baseline=False,
        law=_OBBBA,
    ),
    "amt-extend-tcja-relief": PolicyStatus(
        "superseded", _OBBBA_NOTE, on_current_baseline=False, law=_OBBBA
    ),
    "salt-cap-repeal": PolicyStatus(
        "superseded",
        "The July 2025 reconciliation law (P.L. 119-21) modified the SALT "
        "cap. This preset models full repeal against current law — the "
        "$40,000 cap that reverts to $10,000 in 2030 — not the pre-2025 "
        "$10,000 cap.",
        law=_OBBBA,
    ),
    # ── Biden-administration FY2025 Green Book proposals ─────────────────
    "corporate-28pct": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    "ctc-expansion-2021": PolicyStatus(
        "proposed",
        "Proposal to make the temporary 2021 ARP expansion permanent; "
        "not enacted.",
    ),
    "eitc-childless-expansion": PolicyStatus(
        "proposed",
        "Proposal to make the temporary 2021 ARP expansion permanent; "
        "not enacted.",
    ),
    "estate-exemption-3-5m": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    "step-up-basis-eliminate": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    "niit-expand": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    "gilti-reform": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    "fdii-repeal": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    "international-package": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    "top-rate-39-6": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    # ── Campaign / legislative proposals ─────────────────────────────────
    "corporate-15pct": PolicyStatus(
        "proposed",
        "2024 campaign proposal; not enacted — the corporate rate remains "
        "21%.",
    ),
    "ultra-millionaire-surtax-3pp": PolicyStatus(
        "proposed", "Senate proposal; not enacted."
    ),
    # ── Social Security solvency options ─────────────────────────────────
    "ss-cap-90pct": PolicyStatus("proposed", _SS_OPTION_NOTE),
    "ss-donut-250k": PolicyStatus("proposed", _SS_OPTION_NOTE),
    "ss-cap-eliminate": PolicyStatus("proposed", _SS_OPTION_NOTE),
    # ── Tariffs: executive action moved faster than these presets ────────
    "tariff-universal-10pct": PolicyStatus(
        "partially",
        "Broad tariff actions were imposed by executive order in 2025; this "
        "preset models a stylized schedule, not the enacted structure.",
    ),
    "tariff-china-60pct": PolicyStatus(
        "partially",
        "China-focused tariff actions were imposed by executive order in "
        "2025; this preset models a stylized schedule, not the enacted "
        "structure.",
    ),
    "tariff-reciprocal": PolicyStatus(
        "partially",
        "Reciprocal-tariff actions were imposed by executive order in 2025; "
        "this preset models a stylized schedule, not the enacted structure.",
    ),
    # ── IRA clean-energy credits ─────────────────────────────────────────
    "ira-clean-energy-repeal": PolicyStatus(
        "partially",
        "P.L. 119-21 terminated many IRA energy credits (JCX-35-25 "
        "subchapter A, about $543B) but not the full repeal this preset "
        "models. The score is the pre-enactment full-repeal reconstruction.",
        on_current_baseline=False,
        law=_OBBBA,
    ),
    "ev-credit-repeal": PolicyStatus(
        "superseded",
        "P.L. 119-21 terminated the clean-vehicle credits (JCX-35-25 A.2 "
        "§30D and A.3 §45W). This preset reconstructs repeal as scored "
        "before that law.",
        on_current_baseline=False,
        law=_OBBBA,
    ),
    "ira-clean-energy-extend": PolicyStatus(
        "proposed", "Extension proposal; not enacted."
    ),
    "carbon-tax-50": PolicyStatus(
        "proposed", "Analytic option scored by CBO; never enacted."
    ),
    "carbon-tax-25": PolicyStatus(
        "proposed", "Analytic option scored by CBO; never enacted."
    ),
    # ── ACA premium credits ──────────────────────────────────────────────
    "aca-ptc-extend-enhanced": PolicyStatus(
        "proposed",
        "Extension proposal for the enhanced credits that were scheduled "
        "to lapse after 2025; not enacted.",
    ),
    "aca-ptc-repeal": PolicyStatus(
        "proposed", "Legislative proposal; not enacted."
    ),
}


def get_policy_status(preset: str | None) -> PolicyStatus | None:
    """Status for a preset id or display label, or None when uncurated."""
    if not preset:
        return None
    found = POLICY_STATUS_MAP.get(preset)
    if found is not None:
        return found
    from fiscal_model.preset_ids import PRESET_ID_BY_LABEL

    preset_id = PRESET_ID_BY_LABEL.get(preset)
    if preset_id:
        return POLICY_STATUS_MAP.get(preset_id)
    return None


def scored_on_current_baseline(preset: str | None) -> bool:
    """True when the figure can be labelled with the deployment's baseline.

    Uncurated presets default True: only a known mismatch is withheld.
    """
    status = get_policy_status(preset)
    return status is None or status.on_current_baseline


__all__ = [
    "POLICY_STATUS_MAP",
    "PRE_2025_SCORE_SENTENCE",
    "STATUS_AS_OF",
    "PolicyStatus",
    "get_policy_status",
    "scored_on_current_baseline",
]
