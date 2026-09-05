"""
Transcribed primary sources for the calibrated validation benchmarks.

Phase E of ``planning/VALIDATION_EXPANSION.md`` §5.1 labelled every calibrated
target ``line_item`` / ``secondhand`` / ``model_estimate`` / ``unclassified``
but deliberately stopped short of the actual work: *promoting a* ``secondhand``
*target to* ``line_item`` *requires someone to open the document and transcribe
the row.* This module is that transcription, and it is the single place the
scorecard reads benchmark provenance from.

What a row asserts
------------------
A :class:`BenchmarkSource` with ``provenance="line_item"`` asserts that a human
(or an agent acting under instruction to quote verbatim) opened ``url``, found
``table`` / ``row`` on ``page``, and read ``published_10yr_billions`` there —
and that the figure agrees with the target the repository carries.

``provenance="line_item_differs"`` asserts the same transcription but records a
figure that **disagrees** with the repository's target. The target is *not*
silently moved: retuning a calibrated module to a newly transcribed number
changes model output and is an owner decision, not a bookkeeping one. The
disagreement is carried on the scorecard entry as
``official_10yr_billions_line_item`` and reported in ``docs/VALIDATION.md``.

``provenance="secondhand"`` after this pass means the search happened and
failed: ``searched`` records what was looked for, so the next person does not
repeat it.

``provenance="model_estimate"`` means the record's own source says there is no
published score. Those entries are illustrations and are excluded from every
headline count.

Where the line is drawn
-----------------------
"Agrees" means within :data:`CONFIRMATION_TOLERANCE_PCT` of the published
figure. Anything wider is ``line_item_differs``, however small the modelling
consequence; the point of the pass is that the gap is *stated*, not that it is
negligible. And ``line_item_differs`` is reserved for a source scoring the
**same policy definition**: where the primary document scores a materially
different instrument (a different rate, a different base, a bundle), the record
stays ``secondhand`` and ``searched`` names the nearest published row instead.
Calling a different policy's number "the line item" would be worse than having
no citation at all.

Sign convention
---------------
``published_10yr_billions`` uses the repository's convention — **positive
increases the deficit, negative reduces it** — even when the source publishes
the opposite sign (CBO's options volume tabulates savings as positive, and the
Green Book tabulates revenue gains as positive). The ``row`` text quotes the
source's own label so the flip is checkable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .provenance import (
    LINE_ITEM,
    LINE_ITEM_DIFFERS,
    MODEL_ESTIMATE,
    PROVENANCE_LEVELS,
    SECONDHAND,
)

#: How far a transcribed figure may sit from the repository's target and still
#: count as confirming it, rather than disagreeing with it.
#:
#: 1.5% is where the observed gap distribution splits: every target that is
#: plainly its published figure rounded lands at or under 1.02% ($1,347B for a
#: published $1,349.9B; $220B for $222.2B; $322B for $322.5B; $167B for
#: $166.9B), and the nearest genuine disagreement is 2.5%. The threshold is
#: deliberately not load-bearing — ``published_10yr_billions`` records the
#: transcribed figure on *every* sourced row, confirming or not, so a reader
#: who prefers a different cut can apply it.
CONFIRMATION_TOLERANCE_PCT = 1.5


@dataclass(frozen=True)
class BenchmarkSource:
    """One benchmark's transcribed provenance.

    Attributes:
        policy_id: Scorecard entry this describes.
        provenance: One of :data:`~.provenance.PROVENANCE_LEVELS`.
        document: Full document title, as published.
        publisher: Issuing organization.
        url: Deep link to the document (required for the transcribed labels).
        date: Publication date, ``YYYY-MM`` where the document states a month.
        table: Table name/number the row sits in.
        row: The row label, quoted from the source.
        page: Page reference, e.g. ``"report p. 73; PDF p. 79"``.
        window: The budget window the published figure covers.
        published_10yr_billions: The figure as transcribed, in the repository's
            sign convention. ``None`` when nothing was locatable.
        note: What the transcription established, including any difference
            between the source's policy definition and the module's.
        searched: For ``secondhand`` rows, what was searched and not found.
    """

    policy_id: str
    provenance: str
    document: str = ""
    publisher: str = ""
    url: str | None = None
    date: str | None = None
    table: str | None = None
    row: str | None = None
    page: str | None = None
    window: str | None = None
    published_10yr_billions: float | None = None
    note: str = ""
    searched: str = ""
    #: Other published figures for the same policy, kept so a reader can see
    #: the spread rather than only the one this repository happened to pick.
    alternatives: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.provenance not in PROVENANCE_LEVELS:
            raise ValueError(
                f"{self.policy_id}: unknown provenance {self.provenance!r}"
            )
        if self.provenance in (LINE_ITEM, LINE_ITEM_DIFFERS):
            # ``row`` is in the list deliberately: a transcription that names a
            # table but not the row inside it cannot be checked, which is the
            # whole thing this label is asserting.
            missing = [
                name
                for name in ("url", "date", "table", "row", "page")
                if not getattr(self, name)
            ]
            if missing:
                raise ValueError(
                    f"{self.policy_id}: a transcribed benchmark must cite its "
                    f"document; missing {', '.join(missing)}"
                )
            if self.published_10yr_billions is None:
                raise ValueError(
                    f"{self.policy_id}: a transcribed benchmark must record the "
                    "figure it read"
                )
        if self.provenance == SECONDHAND and not self.searched:
            raise ValueError(
                f"{self.policy_id}: a target left secondhand after the Phase E "
                "pass must record what was searched"
            )


def _index(sources: tuple[BenchmarkSource, ...]) -> dict[str, BenchmarkSource]:
    by_id: dict[str, BenchmarkSource] = {}
    for source in sources:
        if source.policy_id in by_id:
            raise ValueError(f"duplicate benchmark source: {source.policy_id}")
        by_id[source.policy_id] = source
    return by_id


# Shared document handles, so a URL or a page reference is written once.
_CBO_OPTIONS = "CBO, Options for Reducing the Deficit: 2025 to 2034"
_CBO_OPTIONS_URL = "https://www.cbo.gov/publication/60557"
_CBO_OPTIONS_DATE = "2024-12"
_CBO_OPTIONS_WINDOW = "FY2025-2034"

_GREEN_BOOK_FY2025 = (
    "U.S. Treasury, General Explanations of the Administration's Fiscal Year "
    "2025 Revenue Proposals (Green Book)"
)
_GREEN_BOOK_FY2025_URL = (
    "https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf"
)
_GREEN_BOOK_FY2022 = (
    "U.S. Treasury, General Explanations of the Administration's Fiscal Year "
    "2022 Revenue Proposals (Green Book)"
)
_GREEN_BOOK_FY2022_URL = (
    "https://home.treasury.gov/system/files/131/General-Explanations-FY2022.pdf"
)
_GREEN_BOOK_TABLE = "Table of Revenue Estimates (the volume's only table)"
_TREASURY = "U.S. Treasury, Office of Tax Analysis"

# CBO's own site is served behind a bot challenge that returns HTTP 403 to
# every non-browser client, so several CBO figures below were transcribed from
# a *published document that quotes the CBO table verbatim* — usually a CRS
# report, which names the CBO publication it is transcribing in its own source
# note. Those rows say so in their ``note``; the citation is to what was
# actually read, never to a PDF nobody opened.
_CRS_TCJA_EXTENSION = (
    "Congressional Research Service, R48286, 'Reference Table: Expiring "
    "Provisions in the Tax Cuts and Jobs Act (TCJA, P.L. 115-97)'"
)
_CRS_TCJA_EXTENSION_URL = (
    "https://www.congress.gov/crs_external_products/R/HTML/R48286.web.html"
)
_JCX_35_25 = (
    "Joint Committee on Taxation, Estimated Revenue Effects Relative to the "
    "Present Law Baseline of the Tax Provisions in 'Title VII - Finance' of the "
    "Substitute Legislation as Passed by the Senate to Provide for "
    "Reconciliation of the Fiscal Year 2025 Budget, JCX-35-25"
)
_JCX_35_25_URL = (
    "https://www.jct.gov/getattachment/eb21dc77-6439-4fc3-8f5d-fc23a8c377e0/"
    "x-35-25.pdf"
)
_JCT = "Joint Committee on Taxation"
_JCX_35_25_DATE = "2025-07"
_JCX_35_25_WINDOW = "FY2025-2034"
#: JCX-35-25 is one continuous revenue table; the chapter heading is the only
#: sub-division it prints, so it is what identifies where a row sits.
def _jcx_table(chapter: str) -> str:
    return (
        f"Estimated revenue effects table (the document's single table), "
        f"{chapter}"
    )


_CRS_TCJA_TABLE = (
    "Table 1, 'Revenue Costs of Extending the TCJA: Major Provisions "
    "(Billions of Dollars)', transcribing CBO, Budgetary Outcomes Under "
    "Alternative Assumptions About Spending and Revenues (8 May 2024, "
    "publication 60114/60271)"
)


_JCX_CH1 = (
    "Ch.1: Providing Permanent Tax Relief for Middle-Class Families and Workers"
)
#: JCT's chapter heading verbatim, as the CSV carries it since PR #76 replaced
#: the truncated "Ch.1 Permanent Tax Relief". The two are pinned to each other by
#: ``test_pl119_21_sources_match_the_transcribed_csv``.
BENCHMARK_SOURCES: tuple[BenchmarkSource, ...] = (
    # ------------------------------------------------------------------
    # Treasury Green Book rows
    # ------------------------------------------------------------------
    BenchmarkSource(
        policy_id="biden_corporate_28",
        provenance=LINE_ITEM,
        document=_GREEN_BOOK_FY2025,
        publisher=_TREASURY,
        url=_GREEN_BOOK_FY2025_URL,
        date="2024-03",
        table=_GREEN_BOOK_TABLE,
        row="Raise the corporate income tax rate to 28 percent",
        page="report p. 239; PDF p. 247",
        window="FY2025-2034",
        published_10yr_billions=-1_349.9,
        note=(
            "Published $1,349,941 million of revenue over FY2025-2034; the "
            "repository's -$1,347B is that figure rounded (0.2%). Proposal "
            "text (report p. 2): 21% to 28%, effective for taxable years "
            "beginning after 31 December 2023 — the shape the module scores."
        ),
        alternatives=(
            "FY2024 Green Book, same row: $1,325,759M (FY2024-2033).",
            "FY2022 Green Book, same row: $857,817M (FY2022-2031).",
        ),
    ),
    BenchmarkSource(
        policy_id="biden_eitc_childless",
        provenance=LINE_ITEM,
        document=_GREEN_BOOK_FY2025,
        publisher=_TREASURY,
        url=_GREEN_BOOK_FY2025_URL,
        date="2024-03",
        table=_GREEN_BOOK_TABLE,
        row=(
            "Restore and make permanent the American Rescue Plan expansion of "
            "the earned income tax credit for workers without qualifying "
            "children"
        ),
        page="report p. 242; PDF p. 250",
        window="FY2025-2034",
        published_10yr_billions=162.6,
        note=(
            "Published cost $162,553 million (footnote /3: includes the outlay "
            "effect of the refundable portion). The repository carried $178B, "
            "9.5% higher, from no stated table; the Wave 4 provenance lane "
            "adopted this figure through the ledger "
            "(`biden_eitc_childless.v1` -> `.v2`). The credits module's "
            "per-unit constant is still fitted to the superseded $178B and was "
            "deliberately not retuned, which is exactly why the row now "
            "reports a real 9.5% instead of a bookkeeping 0.0%."
        ),
    ),
    BenchmarkSource(
        policy_id="biden_gilti_reform",
        provenance=LINE_ITEM,
        document=_GREEN_BOOK_FY2025,
        publisher=_TREASURY,
        url=_GREEN_BOOK_FY2025_URL,
        date="2024-03",
        table=_GREEN_BOOK_TABLE,
        row=(
            "Revise the global minimum tax regime, limit inversions, and make "
            "related reforms"
        ),
        page="report p. 239; PDF p. 247",
        window="FY2025-2034",
        published_10yr_billions=-373.9,
        note=(
            "Published $373,919 million; the repository carried -$280B, 25% "
            "smaller, with no table behind it, and the Wave 4 provenance lane "
            "adopted this figure through the ledger "
            "(`biden_gilti_reform.v1` -> `.v2`). The proposal text (report "
            "p. 29) confirms the module's shape: QBAI exemption eliminated, "
            "rate to 21%, jurisdiction-by-jurisdiction calculation. The row "
            "title also bundles 'limit inversions, and make related reforms', "
            "which the module does not implement and Treasury does not split, "
            "so the residual is an upper bound on the module's own miss."
        ),
        alternatives=(
            "FY2022 Green Book, 'Revise the global minimum tax regime, "
            "disallow deductions attributable to exempt income, and limit "
            "inversions': $533,503M (FY2022-2031) — this is the row title the "
            "repository's description was copied from.",
            "FY2024 Green Book, same-titled row: $493,341M (FY2024-2033).",
        ),
    ),
    BenchmarkSource(
        policy_id="fdii_repeal",
        provenance=LINE_ITEM,
        document=_GREEN_BOOK_FY2025,
        publisher=_TREASURY,
        url=_GREEN_BOOK_FY2025_URL,
        date="2024-03",
        table=_GREEN_BOOK_TABLE,
        row="Repeal the deduction for foreign-derived intangible income",
        page="report p. 239; PDF p. 247",
        window="FY2025-2034",
        published_10yr_billions=-158.0,
        note=(
            "Gross repeal raises $157,993 million, but Treasury pairs it "
            "one-for-one with 'Provide additional support for research and "
            "development expenditures' (-$157,993M), and the volume prints an "
            "explicit 'Subtotal, Repeal the deduction for foreign-derived "
            "intangible income' of $0. So the repository's -$200B matched "
            "neither the gross row (21% away) nor Treasury's net score (zero). "
            "The module scores repeal without the R&D offset, which is the "
            "gross row, and the Wave 4 provenance lane adopted it through the "
            "ledger (`fdii_repeal.v1` -> `.v2`). Not leakage: the module's "
            "repeal identity runs on FDII income inverted from Treasury OTA's "
            "*tax expenditure* for the deduction ($13.023B/yr), a different "
            "published series from this repeal row."
        ),
        alternatives=(
            "FY2022 Green Book: gross $123,943M, net $0.",
            "FY2024 Green Book: gross $115,621M, net $0.",
        ),
    ),
    BenchmarkSource(
        policy_id="biden_full_international",
        provenance=LINE_ITEM,
        document=_GREEN_BOOK_FY2025,
        publisher=_TREASURY,
        url=_GREEN_BOOK_FY2025_URL,
        date="2024-03",
        table=_GREEN_BOOK_TABLE,
        row="Subtotal, Reform International Taxation",
        page="report p. 240; PDF p. 248",
        window="FY2025-2034",
        published_10yr_billions=-632.2,
        note=(
            "Published subtotal $632,200 million against the repository's old "
            "-$700B (10.7%), adopted through the ledger in Wave 4 "
            "(`biden_full_international.v1` -> `.v2`). Unlike the estate row, "
            "where the module constructs a narrow reform and the document "
            "totals a whole bill, here the *benchmark's own design is the "
            "package* and Treasury prints the package's subtotal — so the "
            "document scores what the label names and the module is what falls "
            "short of it. The three provisions the module actually implements "
            "sum to $510,232M (global minimum tax $373,919M + undertaxed "
            "profits rule $136,313M + FDII net $0), so roughly a fifth of the "
            "target is still provisions it does not carry. The 'BEAT "
            "replacement' named in the repository's old description is not in "
            "the FY2025 volume at all — SHIELD was an FY2022 row ($390,051M) "
            "that the UTPR replaced."
        ),
    ),
    BenchmarkSource(
        policy_id="biden_high_income_tax",
        provenance=LINE_ITEM,
        document=_GREEN_BOOK_FY2025,
        publisher=_TREASURY,
        url=_GREEN_BOOK_FY2025_URL,
        date="2024-03",
        table=_GREEN_BOOK_TABLE,
        row="Increase the top marginal income tax rate for high-income earners",
        page="report p. 242; PDF p. 250",
        window="FY2025-2034",
        published_10yr_billions=-245.9,
        note=(
            "Published $245,924 million; the repository's pre-registered "
            "target was -$252B (2.5% away). The proposal text (report p. 78) "
            "matches the shape exactly: 39.6% on taxable income over $450,000 "
            "married / $400,000 unmarried, C-CPI-U indexed after 2024. This is "
            "an out-of-sample target, so correcting it required a new manifest "
            "row rather than an edit: the Wave 4 provenance lane added "
            "``biden_high_income_tax.v2`` and marked ``.v1`` superseded, and "
            "the manifest's entry-before-scoring rule applies to it as to any "
            "other Tier 1 row. Nothing in the model reads the target, so the "
            "prediction (-$216.5B, bottom-up from SOI with ETI 0.25 on the "
            "ordinary-income base) is unchanged; only the error against it "
            "moves, 14.1% -> 12.0%."
        ),
        alternatives=(
            "FY2024 Green Book, same row: $235,263M (FY2024-2033).",
        ),
    ),
    BenchmarkSource(
        policy_id="medicare_surcharge_2pp",
        provenance=SECONDHAND,
        document=_GREEN_BOOK_FY2025,
        publisher=_TREASURY,
        url=_GREEN_BOOK_FY2025_URL,
        date="2024-03",
        window="FY2025-2034",
        searched=(
            "FY2022/FY2024/FY2025 Green Book revenue tables for a 2pp Medicare "
            "surcharge above $400,000. No row states -$310B. Treasury's "
            "proposal is a **1.2 percentage-point** increase (3.8% to 5.0%, "
            "report p. 77), split across two rows: 'Increase the net "
            "investment income tax rate and additional Medicare tax rate for "
            "high-income taxpayers' $403,790M and 'Apply the net investment "
            "income tax to pass-through business income of high-income "
            "taxpayers' $393,221M (report p. 242; PDF p. 250). The nearest "
            "figure to 310 anywhere is FY2024's pass-through NIIT row "
            "($305,944M), which is a base expansion, not a rate change. The "
            "record's Green Book URL was therefore promoting an unrelated "
            "document to a citation; demoted to secondhand."
        ),
    ),
    BenchmarkSource(
        policy_id="treasury_capgains_39_plus_stepup_elim",
        provenance=LINE_ITEM,
        document=_GREEN_BOOK_FY2022,
        publisher=_TREASURY,
        url=_GREEN_BOOK_FY2022_URL,
        date="2021-05",
        table=_GREEN_BOOK_TABLE + ", American Families Plan section",
        row="Reform the taxation of capital income",
        page="report p. 105; PDF p. 111",
        window="FY2022-2031",
        published_10yr_billions=-322.5,
        note=(
            "Published $322,485 million; the repository's -$322B is that "
            "figure rounded (0.15%). One combined row: Treasury never scores "
            "the rate change and the realization-at-death change separately. "
            "Definition (report p. 62): ordinary rates on LTCG and qualified "
            "dividends above $1,000,000 of AGI, with footnote 1 stating that "
            "'a separate proposal would first increase the top ordinary "
            "individual income tax rate to 39.6 percent (43.4 percent "
            "including the net investment income tax)' — so this row's "
            "incremental rate is 23.8% to 43.4%, i.e. the +19.6pp the record "
            "already carries — plus transfers by gift or at death as "
            "realization events with a $1 million per-person exclusion. "
            "RE-OPENED 2026-09-02 to settle a flag from the capital-gains "
            "lane, which observed that the volume describes the "
            "realization-at-death change as a proposal of its own and asked "
            "whether -$322.0B is the combined figure or the rate-only one. "
            "It is combined, and the table settles it: under 'American "
            "Families Plan — Strengthen taxation of high-income taxpayers' "
            "the Table of Revenue Estimates prints exactly two rows, "
            "'Increase the top marginal income tax rate for high earners' "
            "($131,920M, and zero from 2027 on, because the 39.6% rate "
            "returns by itself when TCJA sunsets) and 'Reform the taxation "
            "of capital income' ($1,241M in 2021 rising to $45,693M in 2031, "
            "$136,263M over 2022-26 and $322,485M over 2022-31). No row "
            "anywhere in the table names transfers, gifts, death, "
            "realization or appreciated property, so the volume publishes no "
            "split of the two sub-proposals its narrative section describes "
            "under one heading. The combined reading stands and the target is "
            "unmoved."
        ),
    ),
    BenchmarkSource(
        policy_id="biden_capital_gains_39",
        provenance=LINE_ITEM,
        document=_GREEN_BOOK_FY2025,
        publisher=_TREASURY,
        url=_GREEN_BOOK_FY2025_URL,
        date="2024-03",
        table=_GREEN_BOOK_TABLE,
        row="Reform the taxation of capital income",
        page="report p. 242; PDF p. 250",
        window="FY2025-2034",
        published_10yr_billions=-288.6,
        note=(
            "Published $288,583 million. The repository previously carried "
            "-$456B, which appears in no Treasury volume; that target is "
            "superseded (see ``preregistered.py``: "
            "``biden_capital_gains_39.v1`` -> ``.v2``). The FY2025 definition "
            "(report p. 88) differs from the FY2022 one in two ways the shape "
            "record now reflects: the threshold is **taxable** income over "
            "$1,000,000 rather than AGI, and the exclusion for gains at death "
            "is **$5 million per donor** (portable, $10M per couple) rather "
            "than $1 million. Same combined row as FY2022 — rate change and "
            "realization at death are never scored apart."
        ),
        alternatives=(
            "FY2024 Green Book, same row: $213,855M (FY2024-2033).",
            "FY2022 Green Book, same row: $322,485M (FY2022-2031) — carried "
            "separately as treasury_capgains_39_plus_stepup_elim.",
        ),
    ),
    BenchmarkSource(
        policy_id="biden_estate_reform",
        provenance=LINE_ITEM_DIFFERS,
        document=(
            "Joint Committee on Taxation, letter from Thomas A. Barthold to "
            "Sen. Bernard Sanders estimating the 'For the 99.5 Percent Act' "
            "(draft GAI21423 NYM)"
        ),
        publisher="Joint Committee on Taxation",
        url=(
            "https://www.sanders.senate.gov/wp-content/uploads/"
            "For-the-99.5-Act-JCT-Score.pdf"
        ),
        date="2021-03",
        table="Estimated revenue effects, fiscal years (billions of dollars)",
        row="Total, For the 99.5 Percent Act",
        page="letter p. 5",
        window="FY2021-2031",
        published_10yr_billions=-429.6,
        note=(
            "The $3.5M exemption / 45% rate design is **not a Treasury "
            "proposal**: no Biden Green Book (FY2022, FY2024 or FY2025) "
            "contains it, and the FY2025 'Subtotal, Modify Estate and Gift "
            "Taxation' is $97,221M of administrative and anti-abuse changes "
            "only. The record's 'Treasury estimate' attribution was wrong and "
            "is corrected here to JCT's score of the bill that does contain "
            "it. Caveat that matters more than the 4.7% gap: the $429.6B "
            "scores the whole ten-section bill (graduated 50/55/65% brackets "
            "above $10M/$50M/$1B, grantor-trust step-up denial, valuation "
            "discounts, 10-year minimum GRATs, GST changes), so it is an "
            "upper bound on the exemption-and-rate change the module models."
        ),
    ),
    # ------------------------------------------------------------------
    # TCJA-extension decomposition (CBO pub 60114/60271 via CRS R48286)
    # ------------------------------------------------------------------
    BenchmarkSource(
        policy_id="extend_tcja_exemption",
        provenance=LINE_ITEM,
        document=_CRS_TCJA_EXTENSION,
        publisher="Congressional Research Service (transcribing CBO)",
        url=_CRS_TCJA_EXTENSION_URL,
        date="2024-11",
        table=_CRS_TCJA_TABLE,
        row="Increased Estate and Gift Exemption",
        page="Table 1",
        window="FY2025-2034",
        published_10yr_billions=166.9,
        note=(
            "$166.9B over FY2025-2034 ($55.2B over FY2025-2029) against the "
            "repository's $167B — the same figure. CRS R47846 states it as "
            "'-$167 billion (FY2025-FY2034)' and attributes it to JCT as well "
            "as CBO, so the record's 'CBO' source string stands. Policy "
            "matches: keep the doubled exemption instead of the 2026 "
            "reversion."
        ),
    ),
    BenchmarkSource(
        policy_id="ctc_extension",
        provenance=LINE_ITEM_DIFFERS,
        document=_CRS_TCJA_EXTENSION,
        publisher="Congressional Research Service (transcribing CBO)",
        url=_CRS_TCJA_EXTENSION_URL,
        date="2024-11",
        table=_CRS_TCJA_TABLE,
        row="Increase and Modification of Child and Dependent Credit",
        page="Table 1",
        window="FY2025-2034",
        published_10yr_billions=735.3,
        note=(
            "$735.3B over FY2025-2034 against the repository's $600B (18.4%). "
            "Part of the gap is definitional and does not favour either "
            "number: CRS notes the published figure 'include[s] the budgetary "
            "impact of the Credit for other dependents', which the credits "
            "module does not score. The 5-year figure is $297.2B. "
            "EXAMINED AND NOT REVISED 2026-09-02 (Wave 4; the reason is in "
            "``target_revisions.EXAMINED_NOT_REVISED``). This row is one of "
            "two published figures for a child-credit extension and both sit "
            "*above* the module's $2,000 flat design rather than bracketing "
            "it: this one adds the other-dependents credit, and JCT's "
            "JCX-35-25 row scores P.L. 119-21's $2,200 indexed credit at "
            "+$816.846B — a figure this repository already carries separately "
            "as the ``pl119_21_child_tax_credit`` benchmark, so adopting it "
            "here would score one JCT row as two benchmarks."
        ),
    ),
    BenchmarkSource(
        policy_id="extend_tcja_amt",
        provenance=LINE_ITEM,
        document=_CRS_TCJA_EXTENSION,
        publisher="Congressional Research Service (transcribing CBO)",
        url=_CRS_TCJA_EXTENSION_URL,
        date="2024-11",
        table=_CRS_TCJA_TABLE,
        row="Increased Alternative Minimum Tax Exemption",
        page="Table 1 (FY2025-FY2034 column)",
        window="FY2025-2034",
        published_10yr_billions=1_357.1,
        note=(
            "The largest disagreement the sourcing pass found, and the owner "
            "decision it left open is now taken: the target was **moved** to "
            "this figure through ``validation/target_revisions.py`` "
            "(extend_tcja_amt.v1 -> .v2), so the row is a confirmation rather "
            "than a disagreement. What the pass established: the published "
            "10-year cost is $1,357.1B and the *five*-year cost in the "
            "adjacent column is $466.2B, against a carried target of $450B — "
            "3.5% from the five-year figure and 66.8% from the ten-year one, "
            "i.e. a five-year cost sitting in a ten-year column. CRS R47846 "
            "states the same 10-year figure as '-$1.4 trillion "
            "(FY2025-FY2034)'. The AMT module's annual constant is still "
            "fitted to the superseded $450B and was deliberately not retuned, "
            "which is why the entry now reports in the unfitted-reconstruction "
            "tier at -66.8%."
        ),
        alternatives=(
            "JCT, JCX-35-25 (1 July 2025), AMT-exemption row of P.L. 119-21: "
            "$1,362.810B over FY2025-2034, 0.4% from this figure. Carried "
            "separately in this repository as the `pl119_21_amt_exemption` "
            "benchmark.",
            "Bipartisan Policy Center, 'The 2025 Tax Debate: The Alternative "
            "Minimum Tax in TCJA', citing JCT: 'Extending the TCJA's "
            "individual AMT changes would reduce revenues by nearly $1.4 "
            "trillion from FY2025 through FY2034.'",
            "TPC T25-0049 implies about $855B for the *standalone* "
            "post-sunset counterfactual (no accompanying rate extension), "
            "which is a different question and is not the target.",
        ),
    ),
    # ------------------------------------------------------------------
    # JCT scores read directly from jct.gov
    # ------------------------------------------------------------------
    BenchmarkSource(
        policy_id="repeal_corporate_amt",
        provenance=LINE_ITEM,
        document=(
            "Joint Committee on Taxation, JCX-18-22, 'Estimated Budget "
            "Effects of the Revenue Provisions of Title I - Committee on "
            "Finance, of an Amendment in the Nature of a Substitute to "
            "H.R. 5376 ... as Passed by the Senate on August 7, 2022'"
        ),
        publisher="Joint Committee on Taxation",
        url=(
            "https://www.jct.gov/getattachment/"
            "efcca154-9fc1-4e72-83c0-d78b9e7372eb/x-18-22.pdf"
        ),
        date="2022-08",
        table="Fiscal Years 2022 - 2031 [Millions of Dollars]",
        row=(
            "Part 1 - Corporate Tax Reform - Corporate Alternative Minimum "
            "Tax (tyba 12/31/22)"
        ),
        page="p. 1",
        window="FY2022-2031",
        # JCT scores CAMT as a $222,248M revenue *raiser*; repealing it costs
        # the deficit the same amount, which is the direction this benchmark
        # scores and the repository's sign convention makes positive.
        published_10yr_billions=222.2,
        note=(
            "$222,248 million as enacted; the repository's $220B is that "
            "rounded, 1.0% away. The record's source string said 'CBO'; the "
            "estimate is JCT's and is corrected here."
        ),
    ),
    BenchmarkSource(
        policy_id="biden_ctc_2021",
        provenance=SECONDHAND,
        document=(
            "CBO, Budgetary Effects of Making Specified Policies in the Build "
            "Back Better Act Permanent (letter to Sen. Graham and Rep. Smith), "
            "publication 57673"
        ),
        publisher="Congressional Budget Office",
        url="https://www.cbo.gov/publication/57673",
        date="2021-12",
        window="FY2022-2031",
        searched=(
            "The document that states this figure is identified but could not "
            "be read: cbo.gov returns HTTP 403 to every non-browser client "
            "(bot challenge), on every path and user-agent, and "
            "web.archive.org was unreachable. Two independent published "
            "transcriptions both give $1.6 trillion for making the ARP child "
            "tax credit permanent over FY2022-2031 — the requesting "
            "committee's own release ('the latest CBO score says the Child Tax "
            "Credit will cost $1.6 trillion') and CRFB's table 'Cost of "
            "Permanent Build Back Better Act, Based on CBO Analysis' ('Expand "
            "the CTC ... $1.60 trillion'). Corroborated but not transcribed, "
            "so it stays secondhand."
        ),
    ),
    BenchmarkSource(
        policy_id="extend_enhanced_ptc",
        provenance=LINE_ITEM,
        document=(
            "CBO letter to Chairman Jodey Arrington and Chairman Jason Smith "
            "on permanently extending the expanded premium tax credits, "
            "publication 60437, as quoted verbatim by the House Budget "
            "Committee"
        ),
        publisher="Congressional Budget Office / Joint Committee on Taxation",
        url="https://www.cbo.gov/publication/60437",
        date="2024-06",
        table="CBO/JCT estimate quoted in the requesting committee's release",
        row=(
            "CBO and JCT estimate that making the policy permanent would "
            "increase the budget deficit by $335 billion over the 2025-2034 "
            "period"
        ),
        page="letter p. 1 (quoted verbatim)",
        window="FY2025-2034",
        published_10yr_billions=335.0,
        note=(
            "The record said 'CBO 2024', and CBO's 2024 figure is $335B over "
            "FY2025-2034 (plus $48B of debt service, giving the $383B headline "
            "some outlets carried); the letter decomposes it as a $415B "
            "increase in the cost of the credit — $250B of outlays and $164B "
            "of forgone revenue — net of $80B of offsetting effects. The "
            "repository's old $350B is CBO/JCT's *September 2025* re-estimate "
            "(publication 61734) on the FY2026-2035 window, per CRS R48290: "
            "'the permanent extension would add approximately $350 billion to "
            "the budget deficit for that time period'. So the number and its "
            "stated vintage disagreed by one budget window, and the record's "
            "declared window (FY2025-2034) picked the fix: the Wave 4 "
            "provenance lane adopted the 2024 figure through the ledger "
            "(`extend_enhanced_ptc.v1` -> `.v2`). The PTC module's annual is "
            "fitted to the superseded $350B and was not retuned. The letter's "
            "addressees were also wrong here — Arrington and Smith, not "
            "Sen. Crapo — and are corrected."
        ),
        alternatives=(
            "CBO/JCT, publication 61734 (18 September 2025): ~$350B over "
            "FY2026-2035, via CRS R48290.",
        ),
    ),
    BenchmarkSource(
        policy_id="repeal_ptc",
        provenance=SECONDHAND,
        document="",
        publisher="Congressional Budget Office",
        date="2024",
        window="FY2025-2034",
        searched=(
            "No published CBO or JCT score of eliminating *all* ACA premium "
            "tax credits was located. Searched: CBO budget-options volumes "
            "2018/2020/2022/2025 (no such option), CBO 'The Premium Tax Credit "
            "and Related Spending' (publication 60523, July 2024 — identified "
            "but unreadable behind cbo.gov's bot challenge), CRS R48290 and "
            "R48286, JCT's estimates of federal tax expenditures. The nearest "
            "published anchor is JCX-48-24 Table 1, 'Subsidies for insurance "
            "purchased through health benefit exchanges', $555.1B over "
            "FY2024-2028 — a baseline tax-expenditure projection with no "
            "coverage response, not a scored repeal, so it cannot stand in "
            "for this target."
        ),
    ),
    BenchmarkSource(
        policy_id="repeal_individual_amt",
        provenance=SECONDHAND,
        document="",
        publisher="Congressional Budget Office",
        date="2024",
        window="FY2026-2035",
        searched=(
            "No CBO budget option or JCT estimate was located for repealing "
            "the individual AMT from 2026, i.e. against a baseline in which "
            "TCJA's larger exemption has already lapsed. Searched: CBO "
            "Options for Reducing the Deficit 2025-2034 (a savings volume; it "
            "would not carry a cost option), CRS R48286/R47846, jct.gov "
            "publications. The nearest primary figure is JCX-46-17 (2 November "
            "2017) p. 3, 'G. Repeal of Alternative Minimum Tax on "
            "Individuals ... -695.5' over FY2018-2027 — repeal measured "
            "against *pre-TCJA* law, a different baseline and a different "
            "decade, so not comparable. "
            "SEARCHED AGAIN 2026-09-02, in the pass that corrected "
            "`extend_tcja_amt` and `universal_insulin_cap`, and the answer is "
            "still no: TPC publishes no 'repeal the individual AMT' model "
            "estimate at any date, JCT and CBO publish no post-2025 repeal "
            "score, and the Bipartisan Policy Center's 2025 tax-debate "
            "explainer — which does quote JCT's $1.4T for *extending* the "
            "exemption and JCT's $637B for TCJA's original AMT change — has no "
            "repeal figure either. The one published quantity that fits the "
            "policy is TPC's own T25-0049 AMT-revenue column, which sums to "
            "$948.9B over 2026-2035 on exactly this baseline. It is "
            "**deliberately not adopted as the target**, for two independent "
            "reasons. (1) It is a baseline projection of what the AMT will "
            "raise, not a scored repeal — the same rule that stops JCX-48-24's "
            "exchange-subsidy projection standing in for `repeal_ptc` above. "
            "(2) It is `amt.py`'s own input: the module's derived path reads "
            "that CSV and reproduces the column year for year, so adopting it "
            "would manufacture a 0% row out of the leakage pattern `loo.py` "
            "already guards against. Two things the owner should still weigh: "
            "$450B is traceable to nothing, and it is internally incoherent "
            "with the transcribed $1,357.1B for merely extending the exemption "
            "— a full repeal cannot cost less than a partial one on the same "
            "baseline. It is left in force because `repeal_individual_amt` is "
            "a locked id in `holdout.py`'s "
            "revenue-scorecard-post-lock-2026-05-02 protocol, which has no "
            "re-registration path, and moving a locked target to an "
            "unpublished figure would fail a release gate on the strength of a "
            "number no document states."
        ),
    ),
    # ------------------------------------------------------------------
    # International
    # ------------------------------------------------------------------
    BenchmarkSource(
        policy_id="pillar_two_adoption",
        provenance=LINE_ITEM_DIFFERS,
        document=(
            "Joint Committee on Taxation, JCX-22-23, 'Possible Effects of "
            "Adopting the OECD's Pillar Two, Both Worldwide and in the "
            "United States'"
        ),
        publisher="Joint Committee on Taxation",
        url=(
            "https://www.jct.gov/getattachment/"
            "07a143e4-277b-4344-b230-c499a9c16be3/"
            "OECD-Pillar-Two-Report-June-2023.pdf"
        ),
        date="2023-06",
        table=(
            "Table 2, 'Fiscal Year Federal Tax Receipt Revenue Effects for "
            "Various Scenarios', column 2023-2033"
        ),
        row=(
            "Scenario 4: Rest of the world does not enact Pillar Two; United "
            "States enacts Pillar Two in 2025, but no U.S. UTPR"
        ),
        page="report p. 10",
        window="FY2023-2033",
        published_10yr_billions=-102.6,
        note=(
            "The repository's -$80B matches no scenario JCT publishes; the "
            "nearest revenue-raising one is $102.6B (22% away). The finding "
            "that matters is not the gap but the conditioning: JCT's "
            "raiser scenarios assume the **rest of the world does not enact**. "
            "Under Scenario 2 — the rest of the world enacts and the US enacts "
            "too, which is the state of the world — JCT scores US adoption at "
            "**-$56.5B of receipts**, i.e. a revenue *loss*, the opposite sign "
            "to this benchmark. The module's own note gives a $50-120B range, "
            "and $102.6B is inside it. "
            "The conditioning is now recorded as a **range target** in "
            "``target_revisions.py`` (``pillar_two_adoption.v2``): Scenarios 2 "
            "and 4 are the two JCT publishes for this design — US enacts, no "
            "US UTPR — and they bracket the answer at -$102.6B and +$56.5B of "
            "deficit effect, a range containing zero. This row stays "
            "``line_item_differs`` rather than becoming a confirmation, which "
            "is the point: the carried -$80B is an editorial midpoint, the "
            "gap to the nearest published scenario is real, and a range "
            "revision does not close it — it says no point closes it."
        ),
        alternatives=(
            "Scenario 1 (RoW enacts, US does not): -$122.0B of US receipts.",
            "Scenario 2 (RoW enacts, US enacts): -$56.5B of US receipts.",
            "Scenario 5 (RoW does not enact, US enacts with UTPR): +$236.5B.",
        ),
    ),
    # ------------------------------------------------------------------
    # Trade
    # ------------------------------------------------------------------
    BenchmarkSource(
        policy_id="trump_universal_10",
        provenance=LINE_ITEM,
        document=(
            "Erica York and Alex Durante, 'How Much Revenue Can Tariffs Really "
            "Raise for the Federal Government?', Tax Foundation Fiscal Fact "
            "861"
        ),
        publisher="Tax Foundation",
        url="https://taxfoundation.org/wp-content/uploads/2025/04/FF861.pdf",
        date="2025-04",
        table="Table 3, 'Conventional Revenue Estimates, in Billions'",
        row="10 Percent Universal Tariff, column 2025-2034",
        page="report p. 4",
        window="FY2025-2034",
        published_10yr_billions=-2_171.1,
        note=(
            "Conventional $2,171.1B against the repository's old -$2,000B "
            "(7.9%), adopted through the ledger in Wave 4 "
            "(`trump_universal_10.v1` -> `.v2`). The -$2T was the conventional "
            "figure rounded down, not the dynamic one, but the rounding put it "
            "close enough to Tax Foundation's dynamic $1,721B to be misread as "
            "one; the retaliation tier is $1,443B (report p. 8 and p. 1). "
            "Conventional is the right tier now for a second reason as well: "
            "FF861's conventional column already nets the income-and-payroll "
            "offset (averaging 26.2%), which is the offset lane L8 built into "
            "`trade.py`, so the two measure the same object. Lane L8 also "
            "de-fitted the coverage constant, so nothing in the module is "
            "fitted to either figure. The record's bare "
            "budgetlab.yale.edu/research link is dropped: Yale publishes no "
            "standalone 10-year figure for a 10% universal tariff."
        ),
        alternatives=(
            "Tax Foundation, same policy, dynamic: $1,721B.",
            "Tax Foundation, dynamic with tit-for-tat retaliation: $1,443B.",
        ),
    ),
    BenchmarkSource(
        policy_id="trump_china_60",
        provenance=SECONDHAND,
        document="",
        publisher="Tax Foundation",
        date="2024",
        window="FY2025-2034",
        searched=(
            "No standalone published 10-year figure for a 60% China tariff was "
            "located. Tax Foundation scores it only bundled ('Universal 20% "
            "Tariff on All Imports Plus Additional 50% Tariff on Imports from "
            "China', $3,823.9B conventional over 2025-2034), and its "
            "standalone China blog gives '$200 billion' as an *annual* static "
            "figure with no budget window. CRFB's 10-year estimate is a range "
            "spanning zero: 'as much as $300 billion in net revenue over a "
            "decade or lose as much as $50 billion'. -$500B exceeds CRFB's "
            "upper bound by two-thirds and is only obtainable as a residual "
            "from Tax Foundation's bundle."
        ),
    ),
    BenchmarkSource(
        policy_id="auto_tariff_25",
        provenance=LINE_ITEM,
        document=(
            "Tax Foundation, 'Trump Tariffs: Tracking the Economic Impact of "
            "the Trump Trade War' (a living tracker; read at its 20 August "
            "2026 revision)"
        ),
        publisher="Tax Foundation",
        url=(
            "https://taxfoundation.org/research/all/federal/"
            "trump-tariffs-trade-war/"
        ),
        date="2026-08",
        table="Table 5, 'Detailed Tariff Revenue Estimates'",
        row=(
            "Section 232 Autos, Heavy Trucks, Buses, and Parts, conventional "
            "revenue column"
        ),
        page="Table 5 (2026-2035 column)",
        window="2026-2035",
        published_10yr_billions=-386.2,
        note=(
            "$386.2B conventional ($286.2B dynamic), adopted through the "
            "ledger in Wave 4 (`auto_tariff_25.v1` -> `.v2`). The superseded "
            "-$100B was not a scorekeeper estimate at all: CRFB, its stated "
            "source, itemises no auto tariff in any of five tariff-revenue "
            "posts, and the figure traces to a White House claim stated *per "
            "year* — Peter Navarro, 30 March 2025, 'We're going to raise about "
            "$100 billion with the auto tariffs alone', inside the '$6 to $7 "
            "trillion over the 10-year period' that FactCheck.org and the "
            "Washington Post Fact Checker both ran down as unsupported. So it "
            "was a short-window figure in a ten-year column, the same failure "
            "mode as `extend_tcja_amt`. A point rather than a range because "
            "the second published figure is not a second estimate of the same "
            "thing: Yale Budget Lab (28 March 2025) scores the tariff *as "
            "announced* at '$600-650 billion over 2026-35', before the "
            "trade-deal carve-outs and US-content exceptions the tracker's "
            "as-in-force row reflects. Design gaps that remain, stated rather "
            "than adjusted: the row bundles heavy trucks and buses (at 10%, "
            "not 25%) and parts with passenger vehicles, and neither publisher "
            "applies the module's 65% USMCA carve-out."
        ),
        alternatives=(
            "Yale Budget Lab (28 March 2025), 25% auto tariffs as announced: "
            "$600-650B over 2026-35, conventional.",
            "Tax Foundation, same tracker row, dynamic: $286.2B.",
        ),
    ),
    BenchmarkSource(
        policy_id="steel_tariff_25",
        provenance=SECONDHAND,
        document="",
        publisher="Tax Foundation",
        date="2024",
        window="FY2025-2034",
        searched=(
            "Neither of the repository's two figures is traceable. No Tax "
            "Foundation or TPC publication with a **25%**-rate steel-and-"
            "aluminium 10-year estimate was located; Tax Foundation's tariff "
            "tracker carries only the post-June-2025 **50%** rates and bundles "
            "copper in ('Section 232 Steel, Aluminum, and Copper | $341.4 "
            "conventional | $235.9 dynamic', 2026-2035), and CRFB's "
            "steel/aluminium posts score derivative-product adjustments, not a "
            "base 25% tariff. Of the repository's own two numbers, -$15B is "
            "annual-scale (the module's static is ~$11B/yr) and -$60B is "
            "neither an annual nor a decade figure from any located document. "
            "The key mismatch is fixed (both dictionaries now say -$60B) so "
            "the app shows *a* score, but the score itself remains unsourced. "
            "SEARCHED AGAIN 2026-09-02 (Wave 4), and the negative result now "
            "has a cause rather than only a record: the 25% Section 232 rate "
            "was in force from 12 March 2025 only until 3 June 2025, when it "
            "doubled to 50%, and no scorekeeper published a ten-year estimate "
            "for the ten-week regime. CRS IN12519, the one congressional "
            "product on the tariff, carries no revenue estimate at all (full "
            "text extracted to confirm it). CRFB's two steel/aluminium posts "
            "score *derivative-rule* changes rather than a base tariff (+$70B "
            "through FY2036 in April 2026, revised to -$90B once the "
            "proclamation landed), so their proximity to -$60B is coincidence. "
            "On the derivatives question this pass set out to answer: every "
            "published figure includes derivative products and none separates "
            "with from without, so the distinction cannot be sourced either. "
            "Left in place and left unsourced rather than retired — see "
            "``target_revisions.EXAMINED_NOT_REVISED``."
        ),
        alternatives=(
            "Tax Foundation tariff tracker, Section 232 steel + aluminium + "
            "copper at 50%: $341.4B conventional / $235.9B dynamic, 2026-2035.",
            "CRFB (1 April 2026), cutting the derivative rate 50%->25% while "
            "applying it to full product value: +$70B through FY2036, revised "
            "to -$90B once the proclamation landed.",
        ),
    ),
    BenchmarkSource(
        policy_id="reciprocal_tariffs",
        provenance=LINE_ITEM_DIFFERS,
        document=(
            "Committee for a Responsible Federal Budget, 'How Much Will "
            "Trump's New Tariffs Raise?'"
        ),
        publisher="Committee for a Responsible Federal Budget",
        url="https://www.crfb.org/blogs/how-much-will-trumps-new-tariffs-raise",
        date="2025-04",
        table=(
            "'Ten-Year Scores of Trump's Tariffs, If Made Permanent', fiscal "
            "years 2025-2034"
        ),
        row=(
            "Reciprocal Tariffs: conventional $1.8 trillion (CRFB), $1.5 "
            "trillion (Tax Foundation), $1.4 trillion (Yale Budget Lab); "
            "dynamic $1.6 / $1.2 / $1.0 trillion"
        ),
        page="the post's only table",
        window="FY2025-2034",
        published_10yr_billions=-1_800.0,
        note=(
            "Superseded by a published *range* in Wave 4 "
            "(`reciprocal_tariffs.v1` -> `.v2`, [-$1,800B, -$1,400B]) rather "
            "than by a point, and the row stays `line_item_differs` for the "
            "same reason `pillar_two_adoption` does: the anchor the "
            "registries carry is a figure inside the range, not the "
            "transcribed one, so the gap has to stay visible. The superseded "
            "-$1.2T was a **tier** error, not a magnitude error — it is "
            "exactly Tax Foundation's *dynamic* score, in a scorecard whose "
            "every other target is conventional, and below all three published "
            "conventional estimates. The three modellers scored the same "
            "announced schedule on the same fiscal window and disagree by 29%, "
            "which is what a range asserts and a point cannot. The anchor now "
            "carried is Tax Foundation's $1.5T conventional, chosen because "
            "Tax Foundation is the publisher this repository's other two "
            "tariff benchmarks are scored against. Design caveat the range "
            "does not close: the published estimates score a 10% floor rising "
            "to 50% by halving each partner's bilateral-deficit-to-imports "
            "ratio, exempting steel, aluminium, autos and parts, copper, "
            "pharmaceuticals, semiconductors and lumber, while the module "
            "applies a flat ~20pp to half of goods imports. Yale's separate "
            "*illustrative* reciprocal proposal (18 February 2025, '$2.7-3.5 "
            "trillion over 2026-35') is a different policy again — it matches "
            "partners' tariff *and VAT* rates across goods *and services*, "
            "'the equivalent of a 13 percentage point hike in the US effective "
            "tariff rate' — and bounds nothing here."
        ),
        alternatives=(
            "Tax Foundation, same table, conventional: $1.5T — the figure the "
            "registries now carry as the in-range anchor.",
            "Yale Budget Lab, same table, conventional: $1.4T.",
            "Dynamic tier, same table: $1.6T (CRFB), $1.2T (Tax Foundation), "
            "$1.0T (Yale Budget Lab).",
            "Yale Budget Lab's illustrative reciprocal proposal (18 February "
            "2025), a different design: $2.7-3.5T over 2026-35.",
        ),
    ),
    # ------------------------------------------------------------------
    # Drug pricing
    # ------------------------------------------------------------------
    BenchmarkSource(
        policy_id="universal_insulin_cap",
        provenance=LINE_ITEM,
        document=(
            "CBO, Estimated Budgetary Effects of H.R. 6833, the Affordable "
            "Insulin Now Act, publication 57957"
        ),
        publisher="Congressional Budget Office",
        url="https://www.cbo.gov/publication/57957",
        date="2022-03",
        table="Estimated budgetary effects, by fiscal year, 2022-2031",
        row=(
            "Secs. 2 and 3, Cost-Sharing for Certain Insulin Products: "
            "estimated outlays 6,566; revenues -4,793"
        ),
        page="table p. 1",
        window="FY2022-2031",
        # Outlays +$6.566B and revenues -$4.793B both widen the deficit.
        published_10yr_billions=11.4,
        note=(
            "**Sign inversion, not a magnitude gap — and now corrected on "
            "both sides.** CBO scores a $35 insulin cap extended to private "
            "plans as *adding* about $11.4B to the deficit over FY2022-2031 "
            "($6.566B of outlays plus $4.793B of forgone revenue), because "
            "capping a patient's cost sharing reallocates cost to plans and "
            "to the federal subsidy for them. The repository used to carry it "
            "as a -$15B saving; the target was moved to this row through "
            "``validation/target_revisions.py`` "
            "(universal_insulin_cap.v1 -> .v2) on 2026-09-02, after lane L7 "
            "had fixed the module half (``pharma.py`` used to credit the whole "
            "patient-side cost of insulin to the federal budget and now scores "
            "the federal share of a cost-sharing shift, +$7.0B). The residual "
            "against this figure is ~39% and is an accuracy statement, where "
            "the old 2,869% was a direction dispute between a model and a "
            "benchmark pointing opposite ways."
        ),
        alternatives=(
            "cbo.gov returns HTTP 403 to non-browser clients; the same table "
            "is reported by InsideHealthPolicy, 'CBO: Insulin Cost Cap Hikes "
            "Spending $6.6B, Lowers Revenues $4.8B' (31 March 2022).",
        ),
    ),
    # ------------------------------------------------------------------
    # IRS enforcement
    # ------------------------------------------------------------------
    BenchmarkSource(
        policy_id="ira_enforcement",
        provenance=LINE_ITEM,
        document=(
            "CBO, letter to Rep. Kevin Brady and Rep. Jason Smith, 'Additional "
            "Information About Increased Enforcement by the Internal Revenue "
            "Service', publication 58390"
        ),
        publisher="Congressional Budget Office",
        url="https://www.cbo.gov/publication/58390",
        date="2022-08",
        table="Letter text",
        row=(
            "revenues will increase by $180.4 billion over the 2022-2031 "
            "period"
        ),
        page="letter p. 1",
        window="FY2022-2031",
        published_10yr_billions=-180.4,
        note=(
            "CBO's August 2022 figure is $180.4B of additional revenue, "
            "explicitly revising its earlier $203.7B, and the Wave 4 "
            "provenance lane adopted it through the ledger "
            "(`ira_enforcement.v1` -> `.v2`). The old -$200B was 11% above the "
            "current figure and 2% below the *withdrawn* one — carrying a "
            "superseded estimate is worse than carrying a round one. Two "
            "mismatches this does not close, both model findings rather than "
            "target ones: the *net* deficit effect is roughly $101B once the "
            "$79B of IRS funding is counted (this benchmark scores the revenue "
            "side by construction), and CBO says the act provides $79B of "
            "total IRS funding of which $46B is enforcement, where the module "
            "assumes $80B of enforcement funding. The module's ROI multiplier "
            "is fitted to the superseded figure and was not retuned."
        ),
        alternatives=(
            "CBO's superseded estimate of the same provision: $203.7B.",
            "Net of the $79B appropriation: roughly $101B.",
        ),
    ),
    BenchmarkSource(
        policy_id="double_enforcement",
        provenance=LINE_ITEM_DIFFERS,
        document=(
            "U.S. Treasury, The American Families Plan Tax Compliance Agenda"
        ),
        publisher="U.S. Treasury",
        url=(
            "https://home.treasury.gov/system/files/136/"
            "The-American-Families-Plan-Tax-Compliance-Agenda.pdf"
        ),
        date="2021-05",
        table="Narrative, 'Revenue Estimates' discussion",
        row=(
            "Total additional revenue generated from the $80 billion increase "
            "in the IRS budget over 10 years is estimated to be around $320 "
            "billion during this horizon, which suggests roughly a 4-to-1 ROI"
        ),
        page="report p. 18",
        window="10 years from FY2022",
        published_10yr_billions=-320.0,
        note=(
            "Treasury's $320B is 6% from the repository's -$340B, so the "
            "target is essentially this sentence. The problem is what it is "
            "attached to: $320B is the yield on **$80 billion** of additional "
            "funding, while the module scores **$16B/year (~$160B)** on top of "
            "the IRA baseline — twice the dose against the single-dose "
            "revenue figure. Treasury's $700B headline is the full package "
            "including bank information reporting ($460B of it), which the "
            "module does not implement at all. EXAMINED AND NOT REVISED "
            "2026-09-02 (Wave 4; the reason is in "
            "``target_revisions.EXAMINED_NOT_REVISED``): the dose is not the "
            "only mismatch — Treasury scored its $80B on a **pre-IRA** "
            "baseline in 2021, while this preset scores its increment on top "
            "of the IRA's $80B, so a 6% agreement between the two would "
            "measure nothing."
        ),
    ),
    # ------------------------------------------------------------------
    # Climate / energy
    # ------------------------------------------------------------------
    BenchmarkSource(
        policy_id="repeal_ira_credits",
        provenance=SECONDHAND,
        document="",
        publisher="Congressional Budget Office",
        date="2024-03",
        window="FY2025-2034",
        searched=(
            "The record cites 'CBO, budgetary effects of the energy-related "
            "tax provisions of P.L. 117-169 (upward revision)'. No CBO "
            "publication matching that description was located, and -$783B "
            "appears in no CBO or JCT document found. What does exist: JCT's "
            "original score, JCX-18-22, 'SUBTITLE D - ENERGY SECURITY' = "
            "-$205.2B of revenue over FY2022-2031; JCT's score of the enacted "
            "terminations in JCX-35-25 (1 July 2025) = $499.1B over "
            "FY2025-2034; and CRFB reading CBO's 2024 baseline, which gives "
            "'almost $870 billion through 2031' and 'closer to $800 billion' "
            "through 2033 absent the EPA emissions rule. That last figure is "
            "the likely origin of -783 — and it is a *projection of what the "
            "credits will cost*, not a scored repeal, which is a different "
            "quantity. The climate module's annual constant is this target "
            "restated, so the 0.0% error was never evidence of anything; now "
            "the target is not evidence either."
        ),
        alternatives=(
            "Tax Foundation (October 2024): repealing the IRA green-energy "
            "credits raises about $921B over ten years.",
        ),
    ),
    BenchmarkSource(
        policy_id="repeal_ev_credits",
        provenance=LINE_ITEM,
        document=(
            "Joint Committee on Taxation, JCX-35-25, estimated budget effects "
            "of the revenue provisions of H.R. 1 as passed by the Senate"
        ),
        publisher="Joint Committee on Taxation",
        url=(
            "https://www.jct.gov/getattachment/"
            "eb21dc77-6439-4fc3-8f5d-fc23a8c377e0/x-35-25.pdf"
        ),
        date="2025-07",
        table="Chapter 5, Subchapter A, fiscal years 2025-2034",
        row=(
            "Termination of clean vehicle credit (sec. 30D) 77,829 + "
            "Termination of qualified commercial clean vehicles credit "
            "(sec. 45W) 104,516"
        ),
        page="p. 3 (PDF p. 5)",
        window="FY2025-2034",
        published_10yr_billions=-182.3,
        note=(
            "The module's stated scope is exactly sections 30D and 45W, and "
            "JCT scores terminating those two at $77,829M + $104,516M = "
            "$182,345M over FY2025-2034 — 9.7% from the repository's old "
            "-$200B, and adopted through the ledger in Wave 4 "
            "(`repeal_ev_credits.v1` -> `.v2`). The Phase E pass recorded that "
            "sum as $182.4B; the two rows add to $182.3B, and the figure is "
            "corrected here. Both rows are already transcribed in this "
            "repository in `data_files/validation/pl119_21_jct_line_items.csv`, "
            "so the target is the same arithmetic the P.L. 119-21 block reads. "
            "Adding the used-vehicle credit (sec. 25E, $7.4B) would give "
            "$189.8B, and the module does not score it. The record's 'CBO' "
            "attribution was wrong: this is a JCT estimate. For scale on how "
            "much this number has moved, JCX-18-22 scored the same credits at "
            "$14.2B over FY2022-2031, and the repository's own knowledge base "
            "still carries a $30-60B range."
        ),
        alternatives=(
            "Including sec. 25E (previously-owned clean vehicle credit): "
            "$189.8B.",
        ),
    ),
    # ------------------------------------------------------------------
    # Out-of-sample targets attributed to the Tax Policy Center
    #
    # All three carry a bare taxpolicycenter.org homepage link. TPC's sitemap
    # was enumerated in full (11 sub-sitemaps, ~20,600 URLs, ~6,500
    # model-estimate pages) looking for the tables behind them. None was
    # found. ``top_rate_45`` is retired as a result (plan §5, and
    # ``preregistered.py``); the other two are recorded here as open owner
    # decisions rather than withdrawn, because the plan named only the first.
    # ------------------------------------------------------------------
    BenchmarkSource(
        policy_id="top_rate_45",
        provenance=SECONDHAND,
        document="",
        publisher="Tax Policy Center",
        date="2023",
        window="FY2024-2033",
        searched=(
            "RETIRED, not merely unsourced. TPC's full sitemap contains no "
            "table for a 45% ordinary rate at any date: the only '45 percent' "
            "slugs are the estate-tax top rate and an EITC phase-in rate, none "
            "of TPC's 82 t23-* tables is a top-rate table, and its top-rate "
            "collections are all pre-2010 (36% / 39.6% / 37.5%). CBO and JCT "
            "publish no +8pp top-bracket option; the closest CBO options are "
            "+1pp on all rates (-$1,185.3B) and +2pp on the four highest "
            "brackets (-$569.5B), both already in the battery. PWBM (May 2025, "
            "FY2026-2035) brackets the plausible range at $401.6B for "
            "reverting the top bracket to 39.6% and $222.4B for a new 39.6% "
            "bracket above $1M, which makes -$420B for +8pp above $609,350 "
            "implausibly low."
        ),
    ),
    BenchmarkSource(
        policy_id="illustrative_top_rate_5pp",
        provenance=SECONDHAND,
        document="",
        publisher="Tax Policy Center",
        date="2023-06",
        window="FY2024-2033",
        searched=(
            "Same sweep as top_rate_45, same result: no TPC table states "
            "-$700B for a +5pp top rate above $1M. The record's own name and "
            "notes call it 'Illustrative', which reads as self-declared "
            "synthetic. Kept live because the plan named only top_rate_45 for "
            "retirement and withdrawing an in-battery case is an owner "
            "decision; flagged in docs/VALIDATION.md. For scale, PWBM scores a "
            "new 39.6% bracket above $1M — a +2.6pp change on the same "
            "threshold — at $222.4B over FY2026-2035."
        ),
    ),
    BenchmarkSource(
        policy_id="warren_ultramillionaire_surtax_3pp",
        provenance=SECONDHAND,
        document="",
        publisher="Tax Policy Center",
        date="2020",
        window="FY2021-2030",
        searched=(
            "No TPC table states -$350B for a 3pp surtax on AGI above $2M. "
            "TPC's only AGI-surtax revenue table is T19-0037, 'Surtax on "
            "Adjusted Gross Income (AGI) Options', 23 September 2019, whose "
            "Option 1 is 'a 10 percent surtax on AGI in excess of $2 million, "
            "unindexed' at $585.3B over 2019-2029 (Option 3, with a $1M "
            "threshold for non-joint filers, $633.9B). That implies roughly "
            "$58.5B per percentage point at the $2M threshold, so a 3pp "
            "version is on the order of $175B — about half the carried target. "
            "The record's ``agi_inclusive_base=True`` flag is confirmed "
            "correct by TPC's definition (the surtax applies to AGI in excess "
            "of the threshold); the magnitude is what is unsupported."
        ),
        alternatives=(
            "TPC T19-0037 Option 1: 10pp surtax on AGI over $2M = $585.3B "
            "(2019-2029), i.e. ~$58.5B per percentage point.",
        ),
    ),
    # ------------------------------------------------------------------
    # Payroll
    # ------------------------------------------------------------------
    BenchmarkSource(
        policy_id="ss_cap_90_pct",
        provenance=LINE_ITEM,
        document=(
            "CBO, Options for Reducing the Deficit: 2019 to 2028, revenue "
            "option 'Increase the Maximum Taxable Earnings for the Social "
            "Security Payroll Tax'"
        ),
        publisher="Congressional Budget Office",
        url="https://www.cbo.gov/budget-options/54806",
        date="2018-12",
        table="Option table, Billions of Dollars, FY2019-2028",
        row="Raise Taxable Share to 90 Percent — Change in Revenues",
        page="option page 54806",
        window="FY2019-2028",
        published_10yr_billions=-804.9,
        note=(
            "$804.9B of additional revenue over FY2019-2028 (deficit reduction "
            "$785.1B once the benefit effect is netted); the repository's "
            "-$800B is that rounded, 0.6% away. The payroll module scores "
            "revenue, so the revenue line is the right comparison. Worth "
            "recording that this is the **2018** volume: CBO's 2024 volume "
            "scores the same option at $727.6B (Option 62, report p. 73; PDF "
            "p. 79), 10.6% lower, which is roughly the size of the residual "
            "the module is asked to close."
        ),
        alternatives=(
            "Same option, deficit-reduction line: $785.1B.",
            "CBO Options 2025-2034, Option 62 alternative 1: $727.6B.",
        ),
    ),
    BenchmarkSource(
        policy_id="ss_donut_250k",
        provenance=SECONDHAND,
        document="",
        publisher="Social Security Administration, Office of the Chief Actuary",
        date="2025",
        window="unstated",
        searched=(
            "The record credits the Social Security Trustees, and OCACT does "
            "score this provision — E2.5, 'Apply 12.4 percent payroll tax rate "
            "on earnings above $250,000 starting in 2026...' — but **publishes "
            "no dollar figures for it at all**. Its detailed table (run 418) "
            "reports only percentages of taxable payroll and trust-fund "
            "ratios: change in the long-range actuarial balance +2.50% of "
            "payroll, reserve depletion moving 2034 to 2057. So -$2.7T cannot "
            "come from the cited source. The widely repeated '$2.7 trillion "
            "over 10 years' traces only to a Peter G. Peterson Foundation "
            "explainer that attributes it to 'the Social Security Trustees' "
            "with no report year and no run number. Published 10-year dollar "
            "figures for the same design are roughly half that: CBO (13 "
            "December 2018) $1,222.6B over FY2019-2028, and CBO's 2024 volume "
            "$1,426.8B over FY2025-2034 (Option 62 alternative 2)."
        ),
        alternatives=(
            "CBO, Options 2019-2028: $1,222.6B.",
            "CBO, Options 2025-2034, Option 62 alternative 2: $1,426.8B.",
        ),
    ),
    BenchmarkSource(
        policy_id="ss_eliminate_cap",
        provenance=SECONDHAND,
        document="",
        publisher="Social Security Administration, Office of the Chief Actuary",
        date="2025",
        window="unstated",
        searched=(
            "Same result as ss_donut_250k and for the same structural reason. "
            "OCACT provision E2.1 ('Eliminate the taxable maximum in years "
            "2026 and later... Do not provide benefit credit for earnings "
            "above the current-law taxable maximum') is scored only in "
            "percent-of-taxable-payroll terms: run 415 gives +2.55% of payroll "
            "and moves depletion from 2034 to 2059. OCACT publishes no "
            "ten-year dollar amount for any payroll provision, so no Trustees "
            "document can be the source of -$3.2T."
        ),
    ),
    BenchmarkSource(
        policy_id="expand_niit",
        provenance=LINE_ITEM,
        document=(
            "Joint Committee on Taxation, JCX-46-21, 'Estimated Budget Effects "
            "of the Revenue Provisions of Title XIII - Committee on Ways and "
            "Means, of H.R. 5376, the \"Build Back Better Act,\" as Passed by "
            "the House of Representatives'"
        ),
        publisher="Joint Committee on Taxation",
        url=(
            "https://www.jct.gov/getattachment/"
            "c18fa669-9b7f-479b-931e-a735e77bce95/x-46-21.pdf"
        ),
        date="2021-11",
        table="Fiscal Years 2022 - 2031 [Millions of Dollars]",
        row=(
            "Subtitle H, Part 2, item 1: Application of net investment income "
            "tax to trade or business income of certain high income "
            "individuals (tyba 12/31/21)"
        ),
        page="p. 6",
        window="FY2022-2031",
        published_10yr_billions=-252.2,
        note=(
            "$252,163 million; the repository's -$250B is that rounded, 0.9% "
            "away, and the record's 'JCT (Build Back Better)' attribution is "
            "exactly right. Two later estimates of a similar base expansion "
            "are much larger and are *not* this benchmark: the FY2025 Green "
            "Book's 'Apply the net investment income tax to pass-through "
            "business income of high-income taxpayers' ($393,221M, "
            "FY2025-2034) and CBO's 2024 Option 53 ($420.0B, FY2025-2034)."
        ),
    ),
    # ------------------------------------------------------------------
    # Tax expenditures
    # ------------------------------------------------------------------
    BenchmarkSource(
        policy_id="eliminate_salt",
        provenance=LINE_ITEM,
        document=_CBO_OPTIONS,
        publisher="Congressional Budget Office",
        url=_CBO_OPTIONS_URL,
        date=_CBO_OPTIONS_DATE,
        table="Option 49, 'Eliminate or Limit Itemized Deductions'",
        row="Eliminate state and local tax deductions",
        page="report p. 59; PDF p. 65",
        window=_CBO_OPTIONS_WINDOW,
        published_10yr_billions=-1_621.0,
        note=(
            "$1,621.0B against the repository's old -$1,200B (35%), adopted "
            "through the ledger in Wave 4 (`eliminate_salt.v1` -> `.v2`). "
            "CBO's option is the clean match to the policy label — eliminate "
            "the SALT deduction, nothing else — on the same ten-year window, "
            "and it is the option the expenditure module's own SALT "
            "`limitation` block already cites for the cap's lapse date. The "
            "record's 'JCT estimate' attribution had no clean counterpart: "
            "JCT's nearest figure, JCX-46-17 item I.D.1, is $1,253.4B over "
            "FY2018-2027 but repeals most itemized deductions while *keeping* "
            "$10,000 of real property tax, so it is both broader and narrower "
            "than this policy. Baseline caveat recorded rather than corrected: "
            "CBO measures the option on a baseline where the cap lapses after "
            "2025, and P.L. 119-21 has since replaced that world with a "
            "$40,000 cap through 2029 reverting to $10,000 in 2030 — a model "
            "gap needing a baseline-vintage concept the module does not have. "
            "Not leakage: PR #100 replaced the leaked `annual_cost_no_cap = "
            "120.0` (the superseded target over ten) with $89.55B computed "
            "from IRS SOI Table 2.1, so this revision retires the last echo of "
            "that constant rather than creating a new one."
        ),
        alternatives=(
            "JCT JCX-46-17 (2 November 2017) item I.D.1, a broader itemized-"
            "deduction repeal retaining $10,000 of property tax: $1,253.4B "
            "over FY2018-2027.",
            "CBO Option 49, eliminate *all* itemized deductions: $3,423.5B.",
        ),
    ),
    BenchmarkSource(
        policy_id="cap_employer_health",
        provenance=SECONDHAND,
        document="",
        publisher="Congressional Budget Office",
        date="2024",
        window="FY2025-2034",
        searched=(
            "No CBO, JCT or Treasury score of a **$50,000 dollar cap** on the "
            "employer health exclusion exists, because no published option is "
            "designed that way: every one caps at a *percentile of premiums*, "
            "which in dollars is far below $50,000. CBO's 2013 volume caps at "
            "$6,420 individual / $15,620 family (revenues $613B, deficit "
            "-$537B, FY2014-2023); its 2016 volume gives -$429B at the 50th "
            "percentile and -$174B at the 75th (FY2017-2026); its 2022 volume "
            "gives -$893.2B / -$499.8B / -$651.4B (FY2023-2032); and its 2024 "
            "volume (Option 56) gives $965.0B / $521.0B / $697.0B "
            "(FY2025-2034). The repository's -$450B sits inside that spread "
            "but corresponds to no alternative in any volume, so nothing here "
            "can be adopted as its line item."
        ),
        alternatives=(
            "Nearest single figure: CBO Options 2017-2026, 50th-percentile "
            "cap, -$429B deficit effect (4.7% from the carried target, but a "
            "different cap design and an eight-year-older window).",
        ),
    ),
    BenchmarkSource(
        policy_id="eliminate_mortgage",
        provenance=SECONDHAND,
        document="",
        publisher="Congressional Budget Office",
        date="2024",
        window="FY2025-2034",
        searched=(
            "No CBO budget option scores outright repeal of the mortgage "
            "interest deduction post-TCJA; the 2016 volume's nearest option "
            "converts it to a 15% credit ($105.0B, FY2017-2026). JCT publishes "
            "the *tax expenditure* rather than a repeal score: JCX-48-24 Table "
            "1 gives $382.2B over FY2024-2028 and JCX-45-25 gives $261.1B over "
            "FY2025-2029 — a tax expenditure is not a repeal estimate, since "
            "it omits the behavioural and itemisation response. The only "
            "located repeal figure is CRS In Focus IF13190 (23 March 2026) "
            "Table 2, 'Repeal MID $495' over FY2026-2035, which CRS itself "
            "labels its own Yale Tax-Simulator estimate and 'not considered "
            "official for revenue scoring purposes'. -$300B matches none of "
            "these. SEARCHED AGAIN 2026-09-02 (Wave 4) and the answer is "
            "unchanged; recorded in "
            "``target_revisions.EXAMINED_NOT_REVISED``. The one new fact is "
            "that the two simulator estimates that do exist disagree with each "
            "other: Yale's own June 2025 options paper puts full repeal "
            "against current law at 'close to $1.2 trillion' where CRS's "
            "IF13190 run of the same simulator gives $495B, 2.4x apart, which "
            "is itself the argument against adopting either. Two things this "
            "search did settle, both of them handed off as modelling "
            "decisions: the record's `annual_cost = 25.0` is a pre-P.L.119-21 "
            "level (JCT's JCX-45-25, December 2025, puts the capped "
            "expenditure at $45.5B in FY2025 rising to $54.9B in FY2029, "
            "because raising the SALT cap to $40,000 took itemising claimants "
            "from 11.8M to 17.8M returns), and Treasury's FY2027 edition gives "
            "$23.9B falling to $14.1B on the *same* statute — a 2-4x "
            "disagreement driven by Treasury's comprehensive-income baseline "
            "against JCT's normal-tax one. Separately, the record's unsourced "
            "`annual_cost_no_limit = 100.0` is now sourced: it is Treasury "
            "OTA's last pre-TCJA projection of the deduction "
            "($1,003,230M over FY2018-2027 = $100.3B/yr, Tax Expenditures "
            "FY2019 edition, Table 1 row 59), i.e. a pre-TCJA-*law* level and "
            "not a $750,000-debt-limit counterfactual — the acquisition-debt "
            "limit alone is worth about $4B/yr (JCX-35-25, +$39,532M over "
            "FY2025-2034)."
        ),
    ),
    BenchmarkSource(
        policy_id="repeal_salt_cap",
        provenance=LINE_ITEM,
        document=(
            "Penn Wharton Budget Model, Brendan Novak, 'Lifting the SALT Cap: "
            "Estimated Budgetary Effects, 2024 and Beyond'"
        ),
        publisher="Penn Wharton Budget Model",
        url=(
            "https://budgetmodel.wharton.upenn.edu/issues/2024/2/8/"
            "lifting-the-salt-cap-budget-effect"
        ),
        date="2024-02",
        table=(
            "Table 3, 'Conventional budget estimates: Policy Options for the "
            "SALT Cap Against Extended TCJA FY25-34'"
        ),
        row="Repeal SALT Cap",
        page=(
            "Table 3 (the 8 February 2024 brief as updated by its "
            "17 September 2024 addendum)"
        ),
        window="FY2025-2034, against an extended-TCJA baseline",
        published_10yr_billions=1_169.0,
        note=(
            "The Phase E search recorded that JCT has never published a "
            "standalone score for repealing the $10,000 cap, and that is still "
            "true. Wave 4 found where the repository's $1,100B actually came "
            "from: it is Penn Wharton's, rounded. PWBM's Table 2 gives "
            "-$1,116B over FY2024-2033 and its Table 3 -$1,169B over "
            "FY2025-2034, the repository's own window, adopted here through "
            "the ledger (`repeal_salt_cap.v1` -> `.v2`) — 'This proposal, to "
            "eliminate the SALT cap entirely beginning in 2025, would cost an "
            "additional $1,169 billion over the 2025 to 2034 budget window.' "
            "The **baseline is the substance**: this is a marginal, stacked "
            "estimate against a permanent TCJA extension, i.e. against a "
            "permanent $10,000 cap. The same paper's Table 1 scores the "
            "identical reform at -$197B **against current law**, because the "
            "cap was scheduled to expire after 2025 — 5.7x apart, so a target "
            "carried without its baseline is ambiguous by an order of "
            "magnitude. The extended-TCJA figure is the counterfactual the "
            "expenditure module's derived path computes, since it prices "
            "repeal as (unlimited SALT expenditure - limited SALT "
            "expenditure) with the cap in force throughout. Note that the twin "
            "benchmark `eliminate_salt` is scored on the *opposite* baseline "
            "(CBO Option 49's lapsed-cap world); both now state which, rather "
            "than hiding it."
        ),
        alternatives=(
            "PWBM, same paper, Table 1 'Against Current Law Baseline FY24-33': "
            "Repeal SALT Cap -$197B (-48 / -98 / -51, zero thereafter).",
            "PWBM, same paper, Table 2 'Against Extended TCJA FY24-33': "
            "-$1,116B.",
            "JCT JCX-35-25's row for P.L. 119-21's actual SALT provision (a "
            "$40,000 cap through 2029 reverting to $10,000 in 2030): +$946.2B "
            "over FY2025-2034 — carried separately here as "
            "`pl119_21_salt_cap_40k`, and the nearest current-law anchor now "
            "that 'repeal the $10,000 cap' describes no live reform.",
            "JCT JCX-67-17 item I.D.1, the cost of *imposing* the cap bundled "
            "with several other itemized-deduction repeals: $668.4B over "
            "FY2018-2027.",
            "JCT JCX-46-21, an $80,000 cap rather than repeal: +$14.8B over "
            "FY2022-2031, because the near-term revenue loss reverses when the "
            "cap would have expired.",
        ),
    ),
    BenchmarkSource(
        policy_id="cap_charitable",
        provenance=SECONDHAND,
        document="",
        publisher="U.S. Treasury",
        date="2016-02",
        window="FY2017-2026",
        searched=(
            "The 28% limitation the record points at is a real Green Book "
            "proposal with a real score — 'Reduce the value of certain tax "
            "expenditures', $645,538M over FY2017-2026 in the FY2017 Green "
            "Book (report p. 268) and $584,197M over FY2013-2022 in the FY2013 "
            "one. It is not a charitable-deduction cap: the proposal text "
            "(FY2017, report p. 154) limits the value of 'all itemized "
            "deductions' *and* specified exclusions — municipal bond interest, "
            "employer health coverage, retirement contributions, HSAs, "
            "student-loan interest — to 28%. Scoring a charitable-only cap "
            "against a figure three times larger and mostly driven by other "
            "provisions would be worse than leaving it unsourced. CBO's Option "
            "50 caps charitable giving specifically, but by a 2%-of-AGI floor "
            "($347.7B) or cash-only rule ($324.3B), not a rate limitation."
        ),
    ),
    BenchmarkSource(
        policy_id="eliminate_step_up",
        provenance=SECONDHAND,
        document="",
        publisher="U.S. Treasury",
        date="2021-05",
        window="FY2022-2031",
        searched=(
            "Treasury never scores step-up elimination on its own: in every "
            "Green Book it is half of the single combined 'Reform the taxation "
            "of capital income' row (FY2022 $322,485M; FY2025 $288,583M), "
            "together with the ordinary-rate change. The only standalone "
            "published score of taxing gains at death is CBO's Option 51 "
            "alternative 2, 'Include accrued capital gains in the last income "
            "tax return of decedents', $536.1B over FY2025-2034 (report p. 61; "
            "PDF p. 67) — but that alternative has **no exemption**, where "
            "this benchmark models the Biden design's $1M exclusion, so it "
            "scores a materially broader policy and is not this row's line "
            "item. It is already carried separately as the Tier 1 case "
            "cbo_opt51_gains_at_death."
        ),
        alternatives=(
            "CBO Option 51 alternative 1, carryover basis instead of deemed "
            "realization: $196.9B.",
        ),
    ),
    BenchmarkSource(
        policy_id="illustrative_1pp_all",
        provenance=SECONDHAND,
        document="",
        publisher="Joint Committee on Taxation",
        date="2023-01",
        window="FY2023-2032",
        searched=(
            "The manifest already describes this as a JCT rule-of-thumb with "
            "no line item, and nothing was found to change that. The published "
            "figures for the same policy — a uniform +1pp on all ordinary "
            "rates — are CBO's, and both are larger: $1,081.3B over FY2023-2032 "
            "(Options 2023-2032 Vol. I) and $1,185.3B over FY2025-2034 "
            "(Options 2025-2034, Option 45 alternative 1), the latter already "
            "carried as its own Tier 1 case. Listed here so that no benchmark "
            "in either tier is left ``unclassified``."
        ),
        alternatives=(
            "CBO Options 2023-2032 Vol. I: $1,081.3B.",
            "CBO Options 2025-2034 Option 45 alternative 1: $1,185.3B "
            "(carried as cbo_opt45_all_rates_1pp).",
        ),
    ),
    # ------------------------------------------------------------------
    # Illustrations — the record's own source string says there is no
    # published score. Listed so the registry covers every benchmark and the
    # "no unclassified rows" test has something to stand on; excluded from
    # every headline count by the scorecard.
    # ------------------------------------------------------------------
    BenchmarkSource(
        policy_id="tcja_no_salt_cap",
        provenance=MODEL_ESTIMATE,
        publisher="none",
        note=(
            "No agency has scored a TCJA extension with the SALT cap removed "
            "as a package; the '~$1.1T added' is the repository's own "
            "decomposition of the full-extension benchmark."
        ),
    ),
    BenchmarkSource(
        policy_id="tcja_rates_only",
        provenance=MODEL_ESTIMATE,
        publisher="none",
        note=(
            "An illustrative slice of the full extension, not a published "
            "score. The scenario's own note says so."
        ),
    ),
    BenchmarkSource(
        policy_id="trump_corporate_15",
        provenance=MODEL_ESTIMATE,
        publisher="none",
        note=(
            "The scenario's own note reads 'No official score; expected "
            "estimate derived from model.'"
        ),
    ),
    BenchmarkSource(
        policy_id="eliminate_estate_tax",
        provenance=MODEL_ESTIMATE,
        publisher="none",
        note="The scenario's source field literally reads 'Model estimate'.",
    ),
    BenchmarkSource(
        policy_id="expand_drug_negotiation",
        provenance=MODEL_ESTIMATE,
        publisher="none",
        note=(
            "CBO scored the IRA's 20 negotiated drugs (-$237B in the module's "
            "own note); extending that to 50 drugs is the repository's "
            "extrapolation, and -$500B is not a CBO score of anything."
        ),
    ),
    BenchmarkSource(
        policy_id="international_reference_pricing",
        provenance=MODEL_ESTIMATE,
        publisher="none",
        note=(
            "A RAND price-comparison study is a price statistic, not a budget "
            "score; -$100B is the repository's derivation from it."
        ),
    ),
    BenchmarkSource(
        policy_id="carbon_tax_50",
        provenance=MODEL_ESTIMATE,
        publisher="none",
        note=(
            "climate.py documents carbon_tax_behavioral_factor as calibrated "
            "so that $50/ton yields ~$1.7T, and the target restates that. "
            "Scoring against it measures internal consistency only."
        ),
    ),
    # ------------------------------------------------------------------
    # P.L. 119-21 (One Big Beautiful Bill Act) - JCX-35-25 line items
    #
    # The only block in this registry whose target *is* the transcription: the
    # runner reads each target straight out of
    # ``data_files/validation/pl119_21_jct_line_items.csv``, which
    # ``scripts/extract_pl119_21_line_items.py`` built from the PDF and checks
    # against JCT's own printed subtotals. So every row here is ``line_item`` by
    # construction, and ``test_pl119_21_sources_match_the_transcribed_csv``
    # pins these figures against that file so the two cannot drift.
    #
    # ``line_item`` labels the *target*, not the fit. Nothing in the TCJA module
    # is calibrated to an individual JCT row - its one factor is fitted to CBO's
    # $4.6T aggregate - which is why these entries carry
    # ``calibrated_to_target=False`` and sit in the unfitted-reconstruction
    # population.
    # ------------------------------------------------------------------
    BenchmarkSource(
        policy_id="pl119_21_rate_extension",
        provenance=LINE_ITEM,
        document=_JCX_35_25,
        publisher=_JCT,
        url=_JCX_35_25_URL,
        date=_JCX_35_25_DATE,
        table=_jcx_table(_JCX_CH1),
        row=(
            "Extension and limited enhancement of reduced rates "
            "(item 1)"
        ),
        page="PDF p. 1",
        window=_JCX_35_25_WINDOW,
        published_10yr_billions=2193.378,
        note=(
            "JCT prints -2,193,378M of revenue over FY2025-2034, which is "
            "$+2,193.378B of deficit effect in this repository's sign "
            "convention. Maps to the module's Individual Rate Cuts component, which carries one hard-coded aggregate grown at 3.5%/yr and no bracket structure."
        ),
    ),
    BenchmarkSource(
        policy_id="pl119_21_standard_deduction",
        provenance=LINE_ITEM,
        document=_JCX_35_25,
        publisher=_JCT,
        url=_JCX_35_25_URL,
        date=_JCX_35_25_DATE,
        table=_jcx_table(_JCX_CH1),
        row=(
            "Extension and enhancement of increased standard deduction "
            "(item 2)"
        ),
        page="PDF p. 1",
        window=_JCX_35_25_WINDOW,
        published_10yr_billions=1424.682,
        note=(
            "JCT prints -1,424,682M of revenue over FY2025-2034, which is "
            "$+1,424.682B of deficit effect in this repository's sign "
            "convention. The module's Doubled Standard Deduction component is a single national annual cost, so it cannot represent the enhancement above a plain TCJA extension that this row scores."
        ),
    ),
    BenchmarkSource(
        policy_id="pl119_21_personal_exemption_termination",
        provenance=LINE_ITEM,
        document=_JCX_35_25,
        publisher=_JCT,
        url=_JCX_35_25_URL,
        date=_JCX_35_25_DATE,
        table=_jcx_table(_JCX_CH1),
        row=(
            "Termination of deduction for personal exemptions other than temporary senior deduction "
            "(item 3)"
        ),
        page="PDF p. 1",
        window=_JCX_35_25_WINDOW,
        published_10yr_billions=-1807.074,
        note=(
            "JCT prints +1,807,074M of revenue over FY2025-2034, which is "
            "$-1,807.074B of deficit effect in this repository's sign "
            "convention. A revenue raiser. JCT nets the new temporary senior deduction inside this row rather than giving it a line of its own, so the row cannot be decomposed further; the module's offset represents the repeal alone."
        ),
    ),
    BenchmarkSource(
        policy_id="pl119_21_child_tax_credit",
        provenance=LINE_ITEM,
        document=_JCX_35_25,
        publisher=_JCT,
        url=_JCX_35_25_URL,
        date=_JCX_35_25_DATE,
        table=_jcx_table(_JCX_CH1),
        row=(
            "Extension and enhancement of increased child tax credit "
            "(item 4)"
        ),
        page="PDF p. 1",
        window=_JCX_35_25_WINDOW,
        published_10yr_billions=816.846,
        note=(
            "JCT prints -816,846M of revenue over FY2025-2034, which is "
            "$+816.846B of deficit effect in this repository's sign "
            "convention. P.L. 119-21 sets a $2,200 indexed credit; the module's component represents the $2,000 TCJA credit."
        ),
    ),
    BenchmarkSource(
        policy_id="pl119_21_qbi_199a",
        provenance=LINE_ITEM,
        document=_JCX_35_25,
        publisher=_JCT,
        url=_JCX_35_25_URL,
        date=_JCX_35_25_DATE,
        table=_jcx_table(_JCX_CH1),
        row=(
            "Extension and enhancement of deduction for qualified business income "
            "(item 5)"
        ),
        page="PDF p. 1",
        window=_JCX_35_25_WINDOW,
        published_10yr_billions=736.539,
        note=(
            "JCT prints -736,539M of revenue over FY2025-2034, which is "
            "$+736.539B of deficit effect in this repository's sign "
            "convention. Section 199A. The module scores one aggregate annual growing at 4%/yr, with no pass-through income distribution and no phase-in thresholds."
        ),
    ),
    BenchmarkSource(
        policy_id="pl119_21_estate_gift_exemption",
        provenance=LINE_ITEM,
        document=_JCX_35_25,
        publisher=_JCT,
        url=_JCX_35_25_URL,
        date=_JCX_35_25_DATE,
        table=_jcx_table(_JCX_CH1),
        row=(
            "Extension and enhancement of increased estate and gift tax exemption amounts "
            "(item 6)"
        ),
        page="PDF p. 1",
        window=_JCX_35_25_WINDOW,
        published_10yr_billions=211.725,
        note=(
            "JCT prints -211,725M of revenue over FY2025-2034, which is "
            "$+211.725B of deficit effect in this repository's sign "
            "convention. $15M per decedent from 2026, indexed. The module's estate component is an aggregate annual cost, not the exemption/rate machinery in estate.py."
        ),
    ),
    BenchmarkSource(
        policy_id="pl119_21_amt_exemption",
        provenance=LINE_ITEM,
        document=_JCX_35_25,
        publisher=_JCT,
        url=_JCX_35_25_URL,
        date=_JCX_35_25_DATE,
        table=_jcx_table(_JCX_CH1),
        row=(
            "Extension of increased alternative minimum tax exemption amounts, modification of phaseout thresholds, and increased threshold phaseout rate "
            "(item 7)"
        ),
        page="PDF p. 1",
        window=_JCX_35_25_WINDOW,
        published_10yr_billions=1362.81,
        note=(
            "JCT prints -1,362,810M of revenue over FY2025-2034, which is "
            "$+1,362.810B of deficit effect in this repository's sign "
            "convention. The provision also lowers the phaseout thresholds and raises the phaseout rate, which raises revenue relative to a plain extension; the module's single AMT aggregate has no way to represent either."
        ),
    ),
    BenchmarkSource(
        policy_id="pl119_21_salt_cap_40k",
        provenance=LINE_ITEM,
        document=_JCX_35_25,
        publisher=_JCT,
        url=_JCX_35_25_URL,
        date=_JCX_35_25_DATE,
        table=_jcx_table(_JCX_CH1),
        row=(
            "Limitation on individual deductions for certain State and local taxes "
            "(item 20)"
        ),
        page="PDF p. 2",
        window=_JCX_35_25_WINDOW,
        published_10yr_billions=-946.209,
        note=(
            "JCT prints +946,209M of revenue over FY2025-2034, which is "
            "$-946.209B of deficit effect in this repository's sign "
            "convention. DESIGN MISMATCH, stated rather than tuned away: the enacted provision raises the cap to $40,000 with a phase-down above $500,000 of income and reverts to $10,000 after 2029, while the module's SALT component represents the flat $10,000 cap. The target is still this row - it is what the law does - and the resulting error is the block's largest."
        ),
    ),
)


SOURCE_BY_POLICY_ID: dict[str, BenchmarkSource] = _index(BENCHMARK_SOURCES)


def source_for(policy_id: str) -> BenchmarkSource | None:
    """Transcribed source record for a benchmark, if one exists."""
    return SOURCE_BY_POLICY_ID.get(policy_id)


def provenance_for(policy_id: str, default: str = SECONDHAND) -> str:
    """Provenance label for a benchmark, from its transcribed source record."""
    source = SOURCE_BY_POLICY_ID.get(policy_id)
    return source.provenance if source is not None else default


def sources_with_provenance(provenance: str) -> tuple[BenchmarkSource, ...]:
    """Every source record carrying one provenance label, in registry order."""
    return tuple(s for s in BENCHMARK_SOURCES if s.provenance == provenance)


def provenance_tally() -> dict[str, int]:
    """Counts by label across the transcription registry."""
    return {
        level: sum(1 for s in BENCHMARK_SOURCES if s.provenance == level)
        for level in PROVENANCE_LEVELS
    }


__all__ = [
    "BENCHMARK_SOURCES",
    "SOURCE_BY_POLICY_ID",
    "BenchmarkSource",
    "provenance_for",
    "provenance_tally",
    "source_for",
    "sources_with_provenance",
]
