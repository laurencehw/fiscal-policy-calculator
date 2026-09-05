"""
Curated legal status for preset policies ("date the law, not just the data").

Every preset models a policy question that was live on some date; several
have since been enacted, superseded, or partially overtaken by events —
most importantly the July 2025 budget-reconciliation law (H.R. 1, the
"One Big Beautiful Bill Act", P.L. 119-21), which extended the individual
TCJA provisions the flagship presets score as open questions.

The map below is hand-curated. Only presets whose status is known with
confidence carry an entry; everything else renders no chip rather than a
guessed one. Notes deliberately avoid provision-level figures that would
need re-verification — they say what happened and where the preset's score
stands relative to it, not the new law's parameters.

Statuses:
- ``proposed``      — put forward (bill, Green Book, campaign, options
                      analysis) but not enacted.
- ``enacted``       — became law substantially as modeled.
- ``superseded``    — the question the preset scores was overtaken by a
                      later law; the score is a pre-enactment reconstruction.
- ``partially``     — related measures were enacted, but not the schedule
                      the preset models.
"""

from __future__ import annotations

from dataclasses import dataclass

STATUS_AS_OF = "2026-08-30"

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

    @property
    def label(self) -> str:
        return {
            "proposed": "Proposed — not enacted",
            "enacted": "Enacted",
            "superseded": "Superseded by later law",
            "partially": "Partially overtaken by later law",
        }.get(self.status, self.status)

    @property
    def icon(self) -> str:
        return {
            "proposed": "🔵",
            "enacted": "🟢",
            "superseded": "🟠",
            "partially": "🟡",
        }.get(self.status, "⚪")


POLICY_STATUS_MAP: dict[str, PolicyStatus] = {
    # ── TCJA-extension family: overtaken by the July 2025 law ────────────
    "🏛️ TCJA Full Extension (CBO: $4.6T)": PolicyStatus("superseded", _OBBBA_NOTE),
    "🏛️ TCJA Extension (No SALT Cap)": PolicyStatus(
        "superseded",
        _OBBBA_NOTE + " The July 2025 law also modified the SALT cap, so the "
        "no-cap variant modeled here differs from what was enacted.",
    ),
    "🏛️ TCJA Rates Only": PolicyStatus("superseded", _OBBBA_NOTE),
    "🏠 Estate Tax: Extend TCJA (CBO: $167B)": PolicyStatus("superseded", _OBBBA_NOTE),
    "👶 CTC Extension (CBO: $600B)": PolicyStatus("superseded", _OBBBA_NOTE),
    "⚖️ AMT: Extend TCJA Relief ($1.36T)": PolicyStatus("superseded", _OBBBA_NOTE),
    "📋 Repeal SALT Cap ($1.17T)": PolicyStatus(
        "superseded",
        "The July 2025 reconciliation law (P.L. 119-21) modified the SALT "
        "cap. This preset models full repeal against the original \\$10K cap "
        "— the pre-2025 policy question.",
    ),
    # ── Biden-administration FY2025 Green Book proposals ─────────────────
    "🏢 Biden Corporate 28% (CBO: -$1.35T)": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    "👶 Biden CTC Expansion (CBO: $1.6T)": PolicyStatus(
        "proposed",
        "Proposal to make the temporary 2021 ARP expansion permanent; "
        "not enacted.",
    ),
    "💼 EITC Childless Expansion (Treasury: $163B)": PolicyStatus(
        "proposed",
        "Proposal to make the temporary 2021 ARP expansion permanent; "
        "not enacted.",
    ),
    "🏠 Biden Estate Reform (-$450B)": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    "📋 Eliminate Step-Up Basis (-$500B)": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    "💰 Expand NIIT (JCT: -$250B)": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    "🌍 Biden GILTI Reform (-$374B)": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    "🌍 Repeal FDII (-$158B)": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    "🌍 Biden International Package (-$632B)": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    "Biden 2025 Proposal": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    # ── Campaign / legislative proposals ─────────────────────────────────
    "🏢 Trump Corporate 15%": PolicyStatus(
        "proposed",
        "2024 campaign proposal; not enacted — the corporate rate remains "
        "21%.",
    ),
    "Warren Ultra-Millionaire Surtax": PolicyStatus(
        "proposed", "Senate proposal; not enacted."
    ),
    # ── Social Security solvency options ─────────────────────────────────
    "💰 SS Cap to 90% (CBO: -$800B)": PolicyStatus("proposed", _SS_OPTION_NOTE),
    "💰 SS Donut Hole $250K (-$2.7T)": PolicyStatus("proposed", _SS_OPTION_NOTE),
    "💰 Eliminate SS Cap (-$3.2T)": PolicyStatus("proposed", _SS_OPTION_NOTE),
    # ── Tariffs: executive action moved faster than these presets ────────
    "🏭 Trump Universal 10% Tariff (-$2.17T)": PolicyStatus(
        "partially",
        "Broad tariff actions were imposed by executive order in 2025; this "
        "preset models a stylized schedule, not the enacted structure.",
    ),
    "🏭 Trump 60% China Tariff (-$500B)": PolicyStatus(
        "partially",
        "China-focused tariff actions were imposed by executive order in "
        "2025; this preset models a stylized schedule, not the enacted "
        "structure.",
    ),
    "🏭 Reciprocal Tariffs (-$1.5T)": PolicyStatus(
        "partially",
        "Reciprocal-tariff actions were imposed by executive order in 2025; "
        "this preset models a stylized schedule, not the enacted structure.",
    ),
    # ── IRA clean-energy credits: curtailed in part by the July 2025 law ─
    "🌱 Repeal IRA Clean Energy Credits ($783B)": PolicyStatus(
        "partially",
        "The July 2025 reconciliation law curtailed several IRA "
        "clean-energy credits. This preset models full repeal as scored "
        "before that law.",
    ),
    "🌱 Repeal EV Credits ($182B)": PolicyStatus(
        "partially",
        "The July 2025 reconciliation law curtailed clean-vehicle credits. "
        "This preset models repeal as scored before that law.",
    ),
    "🌱 Extend IRA Credits Beyond 2032 ($400B)": PolicyStatus(
        "proposed", "Extension proposal; not enacted."
    ),
    "🌱 Carbon Tax \\$50/ton (-$1.7T)": PolicyStatus(
        "proposed", "Analytic option scored by CBO; never enacted."
    ),
    "🌱 Carbon Tax \\$25/ton (-$1.0T)": PolicyStatus(
        "proposed", "Analytic option scored by CBO; never enacted."
    ),
    # ── ACA premium credits ──────────────────────────────────────────────
    "🏥 Extend ACA Enhanced PTCs ($335B)": PolicyStatus(
        "proposed",
        "Extension proposal for the enhanced credits that were scheduled "
        "to lapse after 2025; not enacted.",
    ),
    "🏥 Repeal ACA Premium Credits (-$1.1T)": PolicyStatus(
        "proposed", "Legislative proposal; not enacted."
    ),
}


def get_policy_status(preset_name: str | None) -> PolicyStatus | None:
    """Status for a preset, or None when no confident curation exists."""
    if not preset_name:
        return None
    return POLICY_STATUS_MAP.get(preset_name)


__all__ = ["POLICY_STATUS_MAP", "STATUS_AS_OF", "PolicyStatus", "get_policy_status"]
