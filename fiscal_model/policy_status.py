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

STATUS_AS_OF = "2026-11-17"

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
    #: True when the preset's score is measured against law as it stood before
    #: P.L. 119-21, not against the current-law baseline the site names. Such a
    #: score answers the pre-2025 question, so surfaces must not label it with
    #: the current baseline, and Build's starting packages leave it out.
    pre_2025_law: bool = False

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
    "🏛️ TCJA Full Extension (CBO: $4.6T)": PolicyStatus("superseded", _OBBBA_NOTE, pre_2025_law=True),
    "🏛️ TCJA Extension (No SALT Cap)": PolicyStatus(
        "superseded",
        _OBBBA_NOTE + " The July 2025 law also modified the SALT cap, so the "
        "no-cap variant modeled here differs from what was enacted.",
        pre_2025_law=True,
    ),
    "🏛️ TCJA Rates Only": PolicyStatus("superseded", _OBBBA_NOTE, pre_2025_law=True),
    "🏠 Estate Tax: Extend TCJA (CBO: $167B)": PolicyStatus("superseded", _OBBBA_NOTE, pre_2025_law=True),
    "👶 CTC Extension (CBO: $600B)": PolicyStatus("superseded", _OBBBA_NOTE, pre_2025_law=True),
    "⚖️ AMT: Extend TCJA Relief ($1.36T)": PolicyStatus("superseded", _OBBBA_NOTE, pre_2025_law=True),
    "📋 Repeal SALT Cap ($1.17T)": PolicyStatus(
        "partially",
        "The July 2025 reconciliation law (P.L. 119-21) raised the SALT cap "
        "to \\$40,000 in 2025, rising 1% a year through 2029 and reverting to "
        "\\$10,000 in 2030. This "
        "preset scores full repeal against that current-law path; the "
        "published figure in its label prices repeal of a permanent \\$10K cap.",
    ),
    "📋 Keep the $40K SALT Cap After 2029": PolicyStatus(
        "proposed",
        "Under P.L. 119-21 the raised cap reverts to \\$10,000 in 2030. "
        "Keeping it is a proposal; not enacted.",
    ),
    # ── Biden-administration FY2025 Green Book proposals ─────────────────
    "🏢 Biden Corporate 28% (Treasury: -$1.35T)": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    "👶 Biden CTC Expansion (JCT: $1.6T)": PolicyStatus(
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
    "Top Rate to 39.6% (Biden FY2025)": PolicyStatus("proposed", _GREEN_BOOK_NOTE),
    # ── Already law ─────────────────────────────────────────────────────
    "🔍 IRA Enforcement Funding (-$180B)": PolicyStatus(
        "enacted",
        "Enacted in the Inflation Reduction Act (2022); later laws rescinded "
        "part of the funding. This preset reconstructs CBO's 2022 score of the "
        "provision as enacted, so it is not new revenue on top of current law.",
    ),
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
    "💰 SS Donut Hole $250K (-$1.43T)": PolicyStatus("proposed", _SS_OPTION_NOTE),
    "💰 Eliminate SS Cap (-$3.2T)": PolicyStatus("proposed", _SS_OPTION_NOTE),
    # ── Tariffs: executive action moved faster than these presets ────────
    "🏭 Trump Universal 10% Tariff (-$2.17T)": PolicyStatus(
        "partially",
        "Broad tariff actions were imposed by executive order in 2025; this "
        "preset models a stylized schedule, not the enacted structure.",
    ),
    "🏭 Trump 60% China Tariff (-$650B)": PolicyStatus(
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
    "🌱 Repeal IRA Clean Energy Credits (-$851B)": PolicyStatus(
        "partially",
        "The July 2025 reconciliation law curtailed several IRA "
        "clean-energy credits. This preset models full repeal as scored "
        "before that law.",
        pre_2025_law=True,
    ),
    "🌱 Repeal EV Credits (-$182B)": PolicyStatus(
        "superseded",
        "The July 2025 reconciliation law (P.L. 119-21) ended the clean-vehicle "
        "credits (secs. 30D and 45W) for vehicles acquired after 30 September "
        "2025; JCT's estimate of that law (JCX-35-25) is the published figure "
        "in this preset's label. This preset scores repeal against pre-2025 "
        "law, where the credits continue.",
        pre_2025_law=True,
    ),
    "🌱 Extend IRA Credits Beyond 2032": PolicyStatus(
        "proposed", "Extension proposal; not enacted."
    ),
    "🌱 Carbon Tax \\$50/ton (-$1.7T)": PolicyStatus(
        "proposed", "Analytic option scored by CBO; never enacted."
    ),
    "🌱 Carbon Tax \\$25/ton": PolicyStatus(
        "proposed", "Analytic option scored by CBO; never enacted."
    ),
    # ── ACA premium credits ──────────────────────────────────────────────
    "🏥 Restore ACA Enhanced PTCs ($350B)": PolicyStatus(
        "proposed",
        "The enhanced credits from the 2021 and 2022 laws lapsed at the end "
        "of 2025. This preset scores restoring them from 2026; not enacted.",
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
