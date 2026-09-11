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
**disagreement**. Two kinds of disagreement live under this one label, and a
row says which:

* the usual kind, a transcribed *figure* that differs from the repository's
  target. The target is not silently moved: retuning a calibrated module to a
  newly transcribed number changes model output and is an owner decision, not
  a bookkeeping one. The disagreement is carried on the scorecard entry as
  ``official_10yr_billions_line_item`` and reported in ``docs/VALIDATION.md``.
* the kind ``scope_differs`` names: the figure is right and the *reform it
  prices* is not the one the module builds. ``biden_corporate_28`` is the
  case that forced the distinction — Treasury's published $1,349,941M is the
  figure this repository carries to within rounding, and since the FY2023
  edition that row has scored a GILTI effective-rate step alongside the
  statutory rate while the factory scored against it sets
  ``gilti_rate_change=0.0``. Calling that ``line_item`` would assert an
  agreement the documents do not support.

A ``line_item_differs`` row must carry at least one of the two: a figure gap
wider than :data:`CONFIRMATION_TOLERANCE_PCT`, or a filled ``scope_differs``.
``test_line_item_differs_carries_the_published_figure`` enforces it, so the
label can never mean "something is wrong here, unspecified".

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
        scope_differs: What the published row prices that the module's shape
            does not, or the reverse. Set on a ``line_item_differs`` row whose
            *figure* agrees with the carried target: the disagreement is in
            the reform, not the number, and without this field such a row
            would be indistinguishable from a confirmation. One sentence,
            naming the mechanism.
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
    scope_differs: str = ""
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
        if self.scope_differs and self.provenance != LINE_ITEM_DIFFERS:
            # A confirmed line item that also declares a scope difference is
            # confirming something the module does not build, which is the one
            # thing this registry must never say quietly.
            raise ValueError(
                f"{self.policy_id}: scope_differs is only meaningful on a "
                f"{LINE_ITEM_DIFFERS} row, not on {self.provenance!r}"
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
        provenance=LINE_ITEM_DIFFERS,
        document=_GREEN_BOOK_FY2025,
        publisher=_TREASURY,
        url=_GREEN_BOOK_FY2025_URL,
        date="2024-03",
        table=_GREEN_BOOK_TABLE,
        row="Raise the corporate income tax rate to 28 percent",
        page="report p. 239; PDF p. 247; chapter report p. 2",
        window="FY2025-2034",
        published_10yr_billions=-1_349.9,
        scope_differs=(
            "Treasury's row is not a rate-only row and has not been one since "
            "the FY2023 edition: the chapter states 'The effective global "
            "intangible low-taxed income (GILTI) rate would increase to 14 "
            "percent under the proposal' (report p. 2), so the printed "
            "$1,349,941M prices a statutory-rate increase AND a GILTI "
            "effective-rate step, while `create_biden_corporate_rate_only` "
            "sets `gilti_rate_change=0.0` and says 'No international changes "
            "- just rate'."
        ),
        note=(
            "Published $1,349,941 million of revenue over FY2025-2034; the "
            "repository's -$1,347B is that figure rounded (0.2%), so the "
            "FIGURE agrees and the REFORM does not — see `scope_differs`, and "
            "`planning/memos/CORPORATE_PER_POINT_YIELD.md`, which established "
            "this. The GILTI leg's size is never printed and cannot be "
            "recovered by differencing editions: FY2022 excludes it (the "
            "global minimum tax is a separate $533,503M row), FY2023 is on a "
            "Build Back Better baseline with a 20% GILTI rate, and "
            "FY2024/FY2025 route 21% -> 14% through the corporate row while a "
            "separate $373,919M international row takes 14% -> 21%. So the "
            "3.7% this row reports is measuring a scope mismatch as well as a "
            "fit, and it cannot be split. The row is also an outlier in its "
            "own literature: on its own window Tax Foundation prices the same "
            "reform 31% lower and PWBM 19% lower, and the memo's normalised "
            "metric puts Treasury's implied marginal base at 79.5% of the "
            "average base against JCT's 55.9%."
        ),
        alternatives=(
            "FY2024 Green Book, same row: $1,325,759M (FY2024-2033); "
            "rate + GILTI, like this one.",
            "FY2022 Green Book, same row: $857,817M (FY2022-2031) — THE ONLY "
            "RATE-ONLY Green Book row, and since 2026-09-05 a benchmark in "
            "its own right (`biden_corporate_28_fy2022`).",
            "Tax Foundation, Biden Budget Tax Proposals (21 June 2024) "
            "Table 4: -$935.8B conventional, FY2025-2034, rate only.",
            "PWBM, President Biden's FY2025 Budget Proposal (22 May 2024) "
            "Table 1: -$1,093B conventional, FY2025-2034, rate only.",
        ),
    ),
    BenchmarkSource(
        policy_id="biden_corporate_28_fy2022",
        provenance=LINE_ITEM,
        document=_GREEN_BOOK_FY2022,
        publisher=_TREASURY,
        url=_GREEN_BOOK_FY2022_URL,
        date="2021-05",
        table=_GREEN_BOOK_TABLE,
        row="Raise the corporate income tax rate to 28 percent",
        page="report p. 104; PDF p. 110; chapter report p. 3 / PDF p. 9",
        window="FY2022-2031",
        published_10yr_billions=-857.8,
        note=(
            "Published $857,817 million of revenue over FY2022-2031, read "
            "from Treasury's own PDF; the annual path is 51,127 / 86,182 / "
            "88,059 / 89,385 / 91,784 / 92,065 / 90,730 / 89,357 / 88,798 / "
            "90,330 ($M) and the five-year subtotal 405,537. **The only "
            "rate-only corporate row in any Green Book**: the chapter's "
            "Proposal section is two sentences and the word GILTI does not "
            "appear in it — the global minimum tax is a separate $533,503M "
            "row — where every edition from FY2023 carries the GILTI "
            "effective rate up with the statutory rate. That is what makes it "
            "worth registering beside `biden_corporate_28`: the same reform, "
            "the same factory, a scope that matches the module's shape, and a "
            "per-point yield 36% lower ($122.55B against $192.85B). The "
            "module cannot reproduce that difference and is not fitted to "
            "this row, which is the point — see the scenario's own "
            "`limitations` for the window offset it is scored across."
        ),
        alternatives=(
            "Tax Foundation, Evaluating Proposals to Increase the Corporate "
            "Tax Rate (24 February 2021) Table 4: -$886.3B conventional over "
            "FY2022-2031, rate only.",
            "PWBM, President Biden's $2.7 Trillion American Jobs Plan "
            "(7 April 2021) Table 1: -$891.6B conventional over FY2022-2031, "
            "rate only. The three houses agree to within 4% on this window, "
            "which they do not on FY2025-2034.",
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
            "document to a citation; demoted to secondhand. "
            "**RETIRED in lane R2.** R2 re-read all three volumes and confirms "
            "every figure above, adding two: the FY2025 volume's FY2025-29 "
            "subtotal for the proposal is $178,466M, and the only '310,0xx' "
            "anywhere in that volume is the child-credit expansion at "
            "-$310,024M - 0.008% from the carried target and a COST, the "
            "opposite sign to the raiser this row scored. Neither coincidence "
            "proves where -$310B came from; what they establish is that it is "
            "not the proposal's. The row is withdrawn because the reform it "
            "scores (2pp) is published by nobody, not because of its error: "
            "the model's 2pp figure sits 1.2% from Treasury's 1.2pp row, so "
            "adopting the document without re-shaping would have bought one of "
            "the tier's best rows with a 1.67x rate mismatch. On Treasury's "
            "own rate the model reads -$245.2B against -$403.8B, 39.3% under."
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
        provenance=LINE_ITEM,
        document=(
            "CBO, Budgetary Effects of Making Specified Policies in the Build "
            "Back Better Act Permanent (letter to Sen. Graham and Rep. Smith), "
            "publication 57673"
        ),
        publisher="Congressional Budget Office",
        url=(
            "https://www.cbo.gov/system/files/2021-12/"
            "57673-BBBA-GrahamSmith-Letter.pdf"
        ),
        date="2021-12",
        table=(
            "Table 1, 'Analysis of Potential Modifications to Selected "
            "Sections of H.R. 5376', column group 'Net Increase or "
            "Decrease (-) in the Deficit, 2022-2031', column 'With "
            "Modifications'"
        ),
        row=(
            "XIII. 137102 | Child tax credit | Make permanent rather than "
            "ending after 2022"
        ),
        page="p. 3 of 5",
        window="FY2022-2031",
        published_10yr_billions=1597.0,
        note=(
            "Transcribed 2026-09-09, and the target is NOT moved: $1,600B is "
            "$1,597B rounded, 0.19% apart and well inside "
            "CONFIRMATION_TOLERANCE_PCT, which is the same verdict "
            "biden_corporate_28 gets at 0.2%. The row is the child credit "
            "ALONE -- the earned income tax credit ($135B) and child care and "
            "preschool ($752B) are separate rows of the same table. What "
            "blocked every earlier attempt was a filename, not only the bot "
            "wall: the letter is `57673-BBBA-GrahamSmith-Letter.pdf`, not "
            "`57673-Graham-Smith-Letter.pdf`, and the latter returns CBO's "
            "own 'Page not Found'. cbo.gov serves DataDome to scripted "
            "clients, so Table 1 was read from the rendered PDF in a browser "
            "and the figure checked twice. ONE THING LEFT TO READ: footnote "
            "(a) on the column header was not captured, so whether $1,597B is "
            "stated net of the letter's interest and enforcement components "
            "is unconfirmed from the footnote itself; the three-component "
            "split is described for the $3.0T headline rather than for the "
            "individual rows."
        ),
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
            "for this target. "
            "SEARCHED AGAIN 2026-09-05, and the carried figure now has a most "
            "likely origin, which is precisely why it is still not adopted. "
            "CBO and JCT's June 2024 baseline projections (Health Insurance "
            "and Its Federal Subsidies, publication 51298, Table 2, read from "
            "CBO's own PDF through a Wayback mirror) print, under 'Premium "
            "tax credits and related spending', $966B of outlays plus $176B "
            "of revenue reductions over FY2025-2034 — $1,142B together, 3.8% "
            "from the -$1,100B this record carries. That makes the target a "
            "BASELINE PROJECTION sitting in a repeal-score column, the same "
            "class of quantity the paragraph above already refuses and the "
            "same one `repeal_individual_amt` refuses TPC's T25-0049 for. "
            "Adopting it would make the row worse (18.5% -> 21.5%), so this "
            "is not a lane declining an improvement. No scored repeal exists "
            "to move to: CBO/JCT publication 61734 (18 September 2025) scores "
            "permanently extending the expanded credit and repealing five "
            "sections of the 2025 reconciliation act, and carries no option "
            "eliminating the credit; the 2017 AHCA/BCRA estimates bundle "
            "subsidy repeal with Medicaid on a pre-enhancement statute and a "
            "2017-2026 window. Recorded in "
            "`target_revisions.EXAMINED_NOT_REVISED` with the modelling "
            "handoff: `create_repeal_ptc` sets `coverage_elasticity=0.0`, so "
            "what the module computes IS a baseline cost, and the mismatch is "
            "in the shape as much as in the target. "
            "THE SHAPE HALF IS NOW CLOSED and the target still is not. Lane W7 "
            "(2026-09-06, `planning/lanes/W7_ptc_repeal_shape.md`) replaced the "
            "fitted $83.0B/yr - which was 1100 / (1.10 x sum of 1.04^t), this "
            "target run backwards through the engine's growth factor - with the "
            "scored vintage's own annual credit path from the table below, net "
            "of pub. 60437's published net-to-gross for a section 36B change "
            "($415B gross, $335B net, so 19.28% never reaches the deficit). "
            "The row moved 18.5% -> 29.6% with no constant retuned, and the "
            "movement is almost entirely VINTAGE: the app serves CBO's "
            "February 2026 baseline, in which the ARPA/IRA enhancement has "
            "lapsed and the credit costs $959B over FY2026-2035, against the "
            "$1,143B this June 2024 table carries over FY2025-2034. Scored on "
            "the June 2024 vintage and window with no coverage response the "
            "mechanism returns that $1,143B - 0.09% from the figure below, "
            "which is how completely a model can reproduce a baseline "
            "projection when asked to, and the sharpest available argument for "
            "not adopting one as a repeal score. "
            "RE-SEARCHED 2026-09-09 (lane H9) and nothing has been published "
            "since. CBO/JCT publication 61734 was read in full: it scores "
            "three policies -- permanently expanding the ARPA structure "
            "($350B), nullifying a June 2025 HHS rule ($40B), and repealing "
            "title VII subtitle B of the 2025 reconciliation act ($272B) -- "
            "every one an extension or a repeal of the act's RESTRICTIONS, "
            "none an elimination of the credit. CBO's cost estimates through "
            "September 2026 contain none (the nearest, H.R. 6703 of "
            "16 December 2025, is association health plans and PBM standards "
            "at -$35.6B); no 2025 or 2026 JCX scores repeal of section 36B; "
            "and the phrase 'premium tax credit' does not appear anywhere in "
            "Tax Foundation's 86-option *Options 3.0*."
        ),
        alternatives=(
            "CBO/JCT, publication 51298 (June 2024) Table 2: premium tax "
            "credit outlays $966B + revenue reductions $176B = $1,142B over "
            "FY2025-2034; the whole 'Premium tax credits and related "
            "spending' subtotal, which adds 1332 waivers, the Basic Health "
            "Program and risk adjustment, is $1,316B. Baseline projections, "
            "not repeal scores.",
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
            "number no document states. "
            "SEARCHED A THIRD TIME 2026-09-09 (lane H9) and the verdict "
            "stands. One document is new and does not qualify: Tax "
            "Foundation's *Options 3.0* (July 2026) Option 38, 'Eliminate the "
            "Individual Alternative Minimum Tax', prints +$271.1B "
            "conventional over 2027-2036 -- but it is scored against "
            "POST-P.L. 119-21 law, where TCJA's enlarged exemption is "
            "permanent, and this benchmark's stated design is repeal against "
            "a baseline in which that exemption has LAPSED. The two baselines "
            "are opposites and repeal costs far more under the second, so "
            "adopting it would score one policy against another's figure. "
            "JCT's standalone line is where Phase E left it (JCX-46-17 p. 3 "
            "row G and JCX-54-17 p. 3 row H, -$695.5B over FY2018-2027, a "
            "pre-TCJA baseline). One observation for the owner, which is a "
            "modelling question rather than a provenance one: P.L. 119-21 "
            "made the enlarged exemption permanent, so the lapsed-exemption "
            "baseline this benchmark is DEFINED on is now a counterfactual "
            "rather than current law."
        ),
        alternatives=(
            "Tax Foundation *Options 3.0* Option 38: +$271.1B conventional "
            "over 2027-2036, on a post-P.L. 119-21 baseline -- the opposite "
            "baseline to this benchmark's design.",
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
        provenance=LINE_ITEM,
        document=(
            "Committee for a Responsible Federal Budget, 'Options to Raise "
            "Tariff Revenue' (17 December 2024)"
        ),
        publisher="Committee for a Responsible Federal Budget",
        url="https://www.crfb.org/blogs/options-raise-tariff-revenue",
        date="2024-12",
        table=(
            "'Tariff Scenarios and Their Net Impact on Revenue', section "
            "'Chinese Tariffs', column 'Conventional Impact (2026-2035)'"
        ),
        row="60% Import Tariff on Chinese Goods",
        page="the post's only revenue table",
        published_10yr_billions=-650.0,
        note=(
            "Target revised 2026-09-09 (target_revisions.trump_china_60.v2) "
            "from a -$500B that was only ever a residual from somebody else's "
            "bundle. This is the only located STANDALONE ten-year "
            "conventional estimate of a 60% tariff on Chinese goods with no "
            "other tariff alongside it, and the adjacent row -- '60% Import "
            "Tariff (Assuming 10% Universal Baseline Tariff) | $575 billion' "
            "-- is what makes the $650B row unambiguously this preset's "
            "shape. Four caveats printed on the table, carried rather than "
            "adjusted: 'these options are based on the FY 2026-2035 budget "
            "window; savings would likely be 15 percent less over the FY "
            "2025-2034 budget window'; 'Numbers are rough and rounded' (to "
            "$5B, 0.8% here); 'Conventional estimates reflect the average of "
            "scenarios where lost trade is and isn't diverted to other "
            "trading partners' and 'assume... that all gained tariff revenue "
            "would be subject to income and payroll tax revenue offsets'; and "
            "an update banner noting the December 2024 estimates predate the "
            "2025 tariffs -- which is about what has since been enacted, not "
            "about the hypothetical this benchmark scores."
        ),
        alternatives=(
            "Same table, '60% Import Tariff (Assuming 10% Universal Baseline "
            "Tariff)': $575B conventional.",
            "Same table, dynamic with retaliation: $550B.",
            "Yale Budget Lab (October 2024) Table 2 p. 6: all twelve "
            "scenarios pair 60% China with a 10% or 20% broad tariff, so none "
            "is China-only.",
        ),
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
            "``target_revisions.EXAMINED_NOT_REVISED``. "
            "RE-SEARCHED 2026-09-09 (lane H9): still nothing. Tax "
            "Foundation's *Options 3.0* (July 2026) adds 86 modelled options "
            "and none is a Section 232 steel rate, so the ten-week 25% regime "
            "remains the one tariff in this repository that no scorekeeper "
            "ever priced."
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
            "pharmaceuticals, semiconductors and lumber. Since lane H8 the "
            "module reconstructs that schedule from the executive order's own "
            "formula applied to 2024 Census bilateral trade, so the shapes "
            "now agree and what is left between them is trade diversion and "
            "the exemption list below HS-4; before H8 it applied a flat ~20pp "
            "to half of goods imports. Yale's separate "
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
        provenance=LINE_ITEM,
        document=(
            "William McBride, 'Testimony: The Inflation Reduction Act's Green "
            "Energy Tax Credits', Tax Foundation, submitted to the U.S. House "
            "Committee on Oversight and Government Reform"
        ),
        publisher="Tax Foundation",
        url=(
            "https://taxfoundation.org/testimony/"
            "inflation-reduction-act-ira-green-energy-tax-credits/"
        ),
        date="2025-05",
        table="Testimony text (the document states the figure in prose)",
        row=(
            "'We have estimated that full repeal of the credits would reduce "
            "deficits by $851 billion over the next decade (2025-2034).'"
        ),
        page="testimony body",
        published_10yr_billions=-851.0,
        note=(
            "Target revised 2026-09-09 "
            "(target_revisions.repeal_ira_credits.v2) from an untraceable "
            "-$783B. The document draws the line this benchmark had been on "
            "the wrong side of, in its own words: 'The latest tax expenditure "
            "estimates from the Treasury Department and JCT indicate the cost "
            "of the credits has grown to about $1.2 trillion over the next "
            "decade (2025-2034)' -- a cost, against $851B of deficit "
            "reduction from eliminating them. WHY NOT JCT: JCX-7-23 (26 April "
            "2023) scores Title III of H.R. 2811, captioned 'REPEAL MARKET "
            "DISTORING GREEN TAX CREDITS' [sic], at a NET TOTAL of $515,078M "
            "over FY2023-2033 -- an actual scorekeeper on actual bill text, "
            "and the first instinct is to prefer it. Two things printed on "
            "the document stop that: footnote [1], 'Estimates of outlay "
            "effects presently unavailable', is attached to eleven of its "
            "lines, so the total is revenue-only; and items 11 and 12 read "
            "'Presently Unavailable', so all three clean-vehicle credits are "
            "outside the total. An acknowledged-incomplete total is a lower "
            "bound, and adopting a lower bound as a point target would "
            "measure the missing lines."
        ),
        alternatives=(
            "JCT JCX-7-23, H.R. 2811 Title III NET TOTAL: $515.078B over "
            "FY2023-2033 (revenue-only; clean-vehicle credits excluded).",
            "CRFB's summary of CBO pub. 59102 lists 'Repeal energy tax "
            "credits and spending' at $540B over FY2024-2033 -- a different "
            "scope (credits plus spending) and a different window.",
            "Tax Foundation's March 2025 blog states the same estimate the "
            "adopted testimony does: repealing all the IRA green-energy "
            "credits raises about $851B over 2025-2034 on a conventional "
            "basis.",
        ),
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
            "threshold — at $222.4B over FY2026-2035. "
            "**RETIRED in lane R2**, which added the half of the search Phase E "
            "did not run: the individual-rate option of all four CBO Options "
            "volumes (2018 pub. 54667 Option 1, 2020 pub. 56783 Option 1, 2022 "
            "pub. 58164 Option 13, 2024 pub. 60557 Option 45). Every "
            "alternative in all four is a uniform change at a bracket boundary "
            "or an AGI surtax at the standard deduction, the fourth-bracket "
            "floor, $20,000/$40,000 or $100,000/$200,000 - no scorekeeper "
            "prices a rate change at a $1,000,000 threshold at all. "
            "ROUTE_TO_8_5.md §1 R2 is the plan that names this row, so the "
            "owner decision docs/VALIDATION.md has carried since Phase E is "
            "taken rather than deferred again."
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
            "of the threshold); the magnitude is what is unsupported. "
            "**RETIRED in lane R2.** R2 read the whole simulation rather than "
            "the one table: *AGI Surtax Options* is thirteen tables, T19-0037 "
            "through T19-0050, and every one of them is a 10 percent surtax - "
            "there is no 3pp table to find, and no CBO Options volume prices a "
            "surtax at a $2M threshold in any of its four editions. Scaling "
            "T19-0037 to 3pp would construct a target rather than read one, "
            "and CBO's own warning that large surtaxes are not proportional "
            "says the scaling would be wrong as well as inadmissible. The "
            "sharper finding is that the row's NAME is wrong: Warren's "
            "Ultra-Millionaire Tax Act is a wealth tax on net worth (2% above "
            "$50M, 3% above $1B), so the 3pp is a wealth rate on an income "
            "base and this shape matches no proposal anybody scored - which is "
            "why no search could have succeeded."
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
        provenance=LINE_ITEM,
        document=(
            "CBO, Options for Reducing the Deficit: 2025 to 2034, "
            "publication 60557, Option 62, 'Increase the Maximum Taxable "
            "Earnings for the Social Security Payroll Tax'"
        ),
        publisher="Congressional Budget Office",
        url="https://www.cbo.gov/publication/60557",
        date="2024-12",
        table=(
            "Option 62 table, stub 'Decrease (-) in the deficit', column "
            "2025-2034"
        ),
        row="Subject earnings greater than $250,000 to payroll taxes",
        page="report p. 73 (PDF p. 79)",
        window="FY2025-2034",
        published_10yr_billions=-1426.8,
        note=(
            "Target revised 2026-09-09 (target_revisions.ss_donut_250k.v2) "
            "from an untraceable -$2,700B. CBO's own text matches the "
            "module's design twice: 'The second alternative would apply the "
            "12.4 percent payroll tax to earnings over $250,000 in addition "
            "to earnings below the maximum taxable amount under current "
            "law... The taxable maximum would continue to grow with average "
            "wages, but the $250,000 threshold would not change, so the gap "
            "between the two would shrink', and 'The current-law taxable "
            "maximum would still be used for calculating benefits, so "
            "scheduled benefits would not change under this alternative' -- "
            "which is OCACT E2.5's 'do not provide benefit credit'. Two "
            "wedges stated rather than adjusted: CBO's table note reads 'An "
            "offset to reflect reduced income and payroll taxes has been "
            "applied to the estimates in this table' and the payroll module "
            "has no such channel; and footnote 'a', 'Estimates include "
            "increased outlays for additional payments of Social Security "
            "benefits', is attached to alternative 1 ONLY, because this "
            "alternative changes no scheduled benefit. cbo.gov returns HTTP "
            "403 to scripted clients; the figure is independently in this "
            "repository, transcribed with its annual path by "
            "scripts/extract_cbo_options.py to "
            "data_files/validation/cbo_options_2025_2034_alternatives.csv "
            "(row 62.2)."
        ),
        alternatives=(
            "Same alternative, 2018 volume (Option 20), revenue line: "
            "$1,222.6B over FY2019-2028.",
            "Same alternative, 2020 volume (Option 17), revenue line: "
            "$1,024.0B over FY2021-2030.",
            "Same alternative, 2022 volume (Option 9), deficit line: "
            "$1,203.9B over FY2023-2032.",
        ),
        searched=(
            "Kept as the record of why the target moved on 2026-09-09. "
            "The record credited the Social Security Trustees, and OCACT does "
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
            "document can be the source of -$3.2T. "
            "RE-SEARCHED 2026-09-09 (lane H9), with one correction and one "
            "trap. THE CORRECTION: the claim above is true of OCACT's "
            "PROVISIONS tables and false of the office. OCACT's letter on the "
            "Medicare and Social Security Fair Share Act (11 July 2023, to "
            "Sen. Whitehouse and Rep. Boyle) Table 1b.n prints 'Total "
            "2023-2032' = $3,035.1B in nominal dollars -- for a $400,000 "
            "DONUT with no benefit credit and, unlike CBO, no income-tax "
            "offset. Different threshold, so not this row's line item, but "
            "the blanket claim needed narrowing. THE TRAP: Tax Foundation, "
            "Alex Durante, 'Uncapping the Payroll Tax Would Be the Largest "
            "Tax Increase in Decades' (24 June 2026), scores the "
            "Moreno-Warren proposal -- 'apply the payroll tax to all "
            "earnings above the cap, with no corresponding changes to "
            "benefits', which IS this design -- at '$3.2 trillion from 2027 "
            "through 2036 on a conventional basis and $1.5 trillion after "
            "accounting for the negative economic effects'. $3.2 trillion "
            "equals the carried figure to the digit the document states, so "
            "`target_revision_problems` would reject it as a supersession "
            "that restates its target, and adopting it as a CONFIRMATION "
            "would assert that a constant chosen to produce -$3.2T "
            "('320.0  # window-average of Trustees $3.2T over 10yr') had "
            "been validated by a document published eighteen months later on "
            "a window this repository does not use. No CBO volume scores "
            "elimination at all: 2018 Option 20, 2020 Option 17, 2022 Option "
            "9 and 2024 Option 62 all offer the same two alternatives, a 90% "
            "taxable share and the $250,000 donut. PGPF's '$3.4 trillion "
            "over 10 years (2026 to 2035)' is explicitly the variant 'while "
            "providing benefit credit for those earnings'. See "
            "target_revisions.EXAMINED_NOT_REVISED."
        ),
        alternatives=(
            "Tax Foundation (24 June 2026): $3.2T conventional / $1.5T "
            "dynamic, 2027-2036, no benefit credit.",
            "SSA OACT, Medicare and Social Security Fair Share Act letter "
            "(11 July 2023) Table 1b.n: $3,035.1B nominal over 2023-2032 -- "
            "a $400,000 donut, not elimination.",
            "PGPF: '$3.4 trillion over 10 years (2026 to 2035)' -- with "
            "benefit credit.",
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
            "can be adopted as its line item. "
            "RE-SEARCHED 2026-09-09 (lane H9), and the carried figure now has "
            "a most likely origin -- which is the reason not to adopt it. "
            "CBO's *Budget Options, Volume 1: Health Care* (December 2008), "
            "Option 9, p. 24, is the ONLY published option that states the "
            "cap in dollars: it would tax contributions 'that together "
            "exceeded $1,440 a month for family coverage or $565 a month for "
            "individual coverage', and JCT scores it at revenues of $452.1B "
            "over FY2009-2018 -- 0.5% from the figure this repository "
            "carries. But CBO derives those dollars from the 75th percentile "
            "of 2010 premiums, and $1,440 a month is $17,280 a year against "
            "the $50,000 cap this benchmark's own description states. So the "
            "target is most likely the right number for a far tighter cap, a "
            "decade early, sitting in this column -- extend_tcja_amt's "
            "five-year-cost-in-a-ten-year-column shape, with nothing to move "
            "it to. Also searched and rejected: the Senate Finance "
            "Committee's May 2009 options paper (discusses capping, publishes "
            "no estimate) and JCT's companion background paper (says the "
            "exclusion 'could be reduced by capping the dollar amount', "
            "prints no table); Urban (May 2013) 75th percentile, $264.0B over "
            "2014-2023; Tax Foundation *Options 3.0* Option 30, 80th "
            "percentile ($14,816 single / $38,185 family), -$318.5B over "
            "2027-2036. See target_revisions.EXAMINED_NOT_REVISED."
        ),
        alternatives=(
            "Nearest single figure: CBO Options 2017-2026, 50th-percentile "
            "cap, -$429B deficit effect (4.7% from the carried target, but a "
            "different cap design and an eight-year-older window).",
        ),
    ),
    BenchmarkSource(
        policy_id="eliminate_mortgage",
        provenance=LINE_ITEM_DIFFERS,
        document=(
            "Tax Foundation, 'Options for Reforming America's Tax Code 3.0: "
            "A Policymaker's Guide to Tax Reform Trade-Offs' (July 2026), "
            "Option 25, 'Eliminate the Home Mortgage Interest Deduction'"
        ),
        publisher="Tax Foundation",
        url=(
            "https://taxfoundation.org/tax-reform-guide/option/"
            "eliminate-the-home-mortgage-interest-deduction/"
        ),
        date="2026-07",
        table="Option 25, '10-Year Change in the Deficit, 2027-2036'",
        row="Conventional Primary Deficit Change",
        page="the option's topline table",
        published_10yr_billions=-495.0,
        note=(
            "Target revised 2026-09-09 to a published RANGE "
            "(target_revisions.eliminate_mortgage.v2): [-$495.0B, -$367.9B], "
            "carried anchor -$367.9B, which is this record's `document` -- "
            "Tax Foundation's Option 25, 'On a conventional basis, this "
            "option would decrease the primary deficit by $367.9 billion over "
            "the budget window', scored on the post-OBBBA baseline it names "
            "('The One Big Beautiful Bill Act made the temporary $750,000 cap "
            "permanent'). `published_10yr_billions` carries the OTHER bound, "
            "CRS IF13190 (23 March 2026) Table 2's 'Repeal MID $495' over "
            "FY2026-2035, so the 35% spread stays visible rather than an "
            "anchor looking like a consensus. Wave 4 left this row on the "
            "premise that the two figures then known 'come from the same "
            "simulator and differ by 2.4x'; the third, independent model "
            "resolves that as a BASELINE gap -- Yale's 'close to $1.2 "
            "trillion' is scored against pre-P.L. 119-21 current law, where "
            "TCJA's standard deduction lapses and the itemising population "
            "roughly doubles. No agency has scored repeal: CBO has published "
            "no post-TCJA option, JCT publishes the tax expenditure "
            "(JCX-48-24 $382.2B FY2024-2028; JCX-45-25 $261.1B FY2025-2029), "
            "and Treasury published no FY2027 Green Book."
        ),
        window="CY2027-2036 (anchor); FY2026-2035 (the other bound)",
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
            "($347.7B) or cash-only rule ($324.3B), not a rate limitation. "
            "RE-SEARCHED 2026-09-09 (lane H9) across CBO's 2011, 2013, 2016, "
            "2018, 2020, 2022 and 2024 volumes, its May 2011 study 'Options "
            "for Changing the Tax Treatment of Charitable Giving' (eleven "
            "options, none a rate cap, and its results stated 'for tax year "
            "2006'), JCT, CRS R45922, TPC and Tax Foundation's *Options 3.0*. "
            "Still nothing charitable-only. One non-official ten-year figure "
            "for the exact design exists and is NOT adopted: CRFB, 'The Tax "
            "Break-Down: Charitable Deduction' (16 December 2013), table "
            "'Revenue Impact from Reforming the Charitable Deduction "
            "(Billions, 2014-2023)', row 'Impose a 28% limit on the value of "
            "the deduction | $75', beneath which CRFB prints 'All scores are "
            "rough estimates and may not match official CBO scores. Scores "
            "were chiefly estimated from a 2011 CBO analysis based on 2006 "
            "data.' A rough estimate off tax-year-2006 microdata on a window "
            "that closed in 2023 is not a target; adopting it would move this "
            "row from 0.3% to 167% on a figure its own publisher declines to "
            "stand behind. Recorded so the next pass does not re-find it and "
            "decide otherwise. See target_revisions.EXAMINED_NOT_REVISED."
        ),
        alternatives=(
            "CRFB (16 December 2013): $75B over 2014-2023 for a 28% limit -- "
            "self-labelled a rough estimate.",
            "CBO 2017-2026 volume, Option 8, 'Limit the tax benefits of "
            "itemized deductions to 28 percent of their total value': "
            "$171.5B, JCT -- all itemized deductions.",
            "Tax Foundation *Options 3.0* Option 24, tightening the OBBBA "
            "limitation 'to 28 cents on the dollar': -$169.0B over "
            "2027-2036 -- all itemized deductions.",
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
            "cbo_opt51_gains_at_death. "
            "RE-SEARCHED 2026-09-09 (lane H9): no published estimate scores "
            "realization at death WITH an exclusion as a standalone "
            "provision, and the carried -$500B is about 2.4x every standalone "
            "figure that exists -- in the direction the design cannot "
            "explain, because an exclusion makes a repeal NARROWER, so the "
            "no-exclusion figures are an upper bound this target sits above. "
            "The STEP Act was searched specifically and JCT has not scored "
            "it: Senator Van Hollen's own one-pager describes the $1 million "
            "exclusion this benchmark models and cites only a JCT TAX "
            "EXPENDITURE, '$41.9 billion in 2021 alone'. Every estimate that "
            "does carry an exclusion is bundled: JCT's JCX-15-16 item XI.B, "
            "'Reform the Taxation of Capital Income', $248,739M FY2016-2026, "
            "is Obama's 28% rate AND gains at death with a $100,000 exclusion "
            "in one line; PWBM's American Families Plan row, $376B "
            "FY2022-2031, is three provisions in one line. See "
            "target_revisions.EXAMINED_NOT_REVISED, which also names this row "
            "as a retirement candidate for the owner."
        ),
        alternatives=(
            "CBO Option 51 alternative 1, carryover basis instead of deemed "
            "realization: $196.9B.",
            "PWBM, 'The Biden Tax Plan' (23 January 2020) Table 1, "
            "'Eliminate stepped-up basis': $204B over FY2021-2030, no "
            "exclusion.",
            "CBO Options 2021-2030, Option 6, 'Change the Tax Treatment of "
            "Capital Gains From Sales of Inherited Assets': $110.3B, JCT, "
            "carryover basis.",
            "Tax Foundation *Options 3.0* Option 15: -$206.4B over "
            "2027-2036, carryover basis, no exclusion.",
        ),
    ),
    BenchmarkSource(
        policy_id="illustrative_1pp_all",
        provenance=LINE_ITEM,
        document=(
            "Options for Reducing the Deficit: 2023 to 2032, Volume I: "
            "Larger Reductions"
        ),
        publisher="Congressional Budget Office",
        url="https://www.cbo.gov/publication/58164",
        date="2022-12",
        table="Option 13 — Revenues, Increase Individual Income Tax Rates",
        row="Raise all tax rates on ordinary income by 1 percentage point",
        page="report p. 72; PDF p. 76",
        window="FY2023-2032",
        published_10yr_billions=-1_081.3,
        note=(
            "Lane R2 moved this row off a rule of thumb and onto the option "
            "its own record already pointed at. Published -$1,081.3B over "
            "FY2023-2032 with the annual path -72.4 / -106.6 / -111.3 / "
            "-102.1 / -102.2 / -107.4 / -112.0 / -117.0 / -122.3 / -127.9 and "
            "a five-year subtotal of -494.6; 'Data source: Staff of the Joint "
            "Committee on Taxation', which is why the record keeps JCT as its "
            "source_name. Everything the manifest claimed for -$960B is true "
            "of this figure instead: the same reform, the same estimator, the "
            "same FY2023-2032 window, the same vintage. "
            "**The row is not a duplicate of cbo_opt45_all_rates_1pp and it is "
            "not scored on its own decade either.** That row is the identical "
            "option in the 2025-2034 volume at -$1,185.3B, and CBO's two "
            "editions differ by $104.0B (9.6%) for one unchanged reform - the "
            "size of a decade of base growth, and the size of most of this "
            "row's residual, because the runner opens its window in FY2025. "
            "FY2022_TARGET_WINDOW_RULE would close it and would move a model "
            "output, so R2 published the number and left the .v3 to the owner. "
            "Read the pair as one measurement of the model's window "
            "insensitivity rather than as two independent observations."
        ),
        alternatives=(
            "CBO Options 2025-2034 Option 45 alternative 1: $1,185.3B "
            "(carried as cbo_opt45_all_rates_1pp, the same reform on the "
            "model's own scoring window).",
            "CBO Options 2020 (pub. 56783) Option 1 alternative 1: $884.0B "
            "over FY2021-2030 — the same reform a third time, and the third "
            "different figure.",
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
        searched=(
            "Searched 2026-09-09 (lane H9). CBO's supplemental workbook for "
            "publication 60114 prints the extension block total $3,255,900M "
            "and, separately, the itemized-deduction row at -$1,244,276M over "
            "FY2025-2034 -- two rows that would have to be added, under CBO's "
            "own warning that the estimates 'do not include all potential "
            "interaction effects of permanently extending the provisions "
            "together'. Summing rows to make a target is what PR #122 "
            "declined for trump_corporate_15's bonus-depreciation leg. ONE "
            "published single row exists and is NOT adopted: CRFB, 'SALT Cap "
            "Expiration Could Be Costly Mistake' (28 August 2024), table "
            "'Fiscal Impact of Various TCJA Extension Scenarios', row 'Extend "
            "except SALT cap' = $5.1 trillion over FY2026-2035, from CRFB's "
            "own Build Your Own Tax Extensions tool. It pairs with that "
            "table's other row, 'Extend all individual and estate provisions "
            "| $3.9 trillion', and this repository scores the base extension "
            "against CBO's $4.6T -- so adopting $5.1T would mix two "
            "publishers' bases inside one decomposition, and most of the "
            "resulting error would be the CRFB-versus-CBO base gap rather "
            "than anything about the SALT cap. The two publications AGREE on "
            "the increment actually at issue: CRFB puts it at +$1.2T and CRS "
            "R48286's itemized-deduction row at $1,244.3B, against the ~$1.1T "
            "this repository assumes. Separately, this search found "
            "CBO_SCORE_MAP quoting $6,500B as Build's list price for this "
            "preset while the benchmark scored against $5,700B; the list "
            "price is now aligned to the benchmark and the target itself "
            "stays unsourced. Also searched: JCT (no JCX scores the "
            "package), Tax Foundation's 2025 TCJA options, PWBM."
        ),
    ),
    BenchmarkSource(
        policy_id="tcja_rates_only",
        provenance=LINE_ITEM,
        document=(
            "Congressional Research Service, R48286, 'Expiring Provisions of "
            "P.L. 115-97 (the Tax Cuts and Jobs Act): Economic Issues', "
            "transcribing CBO, Budgetary Outcomes Under Alternative "
            "Assumptions About Spending and Revenues (8 May 2024, publication "
            "60114/60271)"
        ),
        publisher="Congressional Research Service (transcribing CBO/JCT)",
        url=(
            "https://www.congress.gov/crs_external_products/R/HTML/"
            "R48286.web.html"
        ),
        date="2024-11",
        table=(
            "Table 1, 'Revenue Costs of Extending the TCJA: Major Provisions "
            "(Billions of Dollars)', FY2025-FY2034 column"
        ),
        row="Reduced Individual Tax Rates",
        page="Table 1",
        window="FY2025-2034",
        published_10yr_billions=2158.7,
        note=(
            "Target revised 2026-09-09 "
            "(target_revisions.tcja_rates_only.v2) from +$3,185B, which the "
            "scenario's own note called illustrative ('~$3.2T calibrated'). "
            "$2,158.7B over FY2025-2034 and $821.8B over FY2025-2029; CBO's "
            "own supplemental workbook labels the row '10%, 12%, 22%, 24%, "
            "32%, 35%, and 37% income tax rate brackets', estimator JCT, "
            "effective tyba 12/31/25. This is the SAME table, column and "
            "window this repository already reads extend_tcja_amt's "
            "$1,357.1B out of, so no new document was needed and no summing "
            "was involved -- PR #122's rule against constructing a target by "
            "adding rows never came into play. The standard deduction "
            "($1,251.0B), personal-exemption repeal (-$1,717.5B), child "
            "credit, QBI and AMT are separate rows, which is the scenario's "
            "own design. CRS's table note travels with the figure: 'The "
            "revenue cost depends on the order of estimation due to "
            "interactions between the provisions.'"
        ),
        alternatives=(
            "JCT JCX-35-25 p. 1 row 1, 'Extension and limited enhancement of "
            "reduced rates', -$2,193.4B over FY2025-2034 -- 1.6% away, and "
            "not adopted because the 'limited enhancement' is P.L. 119-21's "
            "rather than TCJA's rate structure.",
        ),
    ),
    BenchmarkSource(
        policy_id="trump_corporate_15",
        provenance=LINE_ITEM_DIFFERS,
        document=(
            "Garrett Watson and Erica York, 'A Lower Corporate Tax Rate Can "
            "Be Part of Broader Tax Reform', Tax Foundation (17 July 2024, "
            "updated 23 October 2024)"
        ),
        publisher="Tax Foundation",
        url="https://taxfoundation.org/blog/trump-corporate-tax-cut/",
        date="2024-07",
        table=(
            "Table 2, 'Revenue Effects of Reducing the Corporate Rate to 15 "
            "Percent (Billions)'"
        ),
        row="Conventional revenue effect, 2025-2034",
        page="Table 2 (the post's only revenue table)",
        window="FY2025-2034",
        published_10yr_billions=595.0,
        scope_differs=(
            "Neither published estimate includes bonus depreciation, and "
            "`create_republican_corporate_cut` sets "
            "`extend_bonus_depreciation=True` — PWBM prints the business "
            "provisions separately at -$623B. Measured on this branch the "
            "module's bonus-depreciation leg is +$294.15B of its +$1,491.8B, "
            "so the rate leg alone reads +$1,197.6B / +77.9% against the "
            "anchor rather than +121.6%."
        ),
        note=(
            "Until 2026-09-05 this row's target was +$1,920B, provenance "
            "`model_estimate` — this repository's own output, by the "
            "scenario's own admission. The ledger "
            "(`target_revisions.trump_corporate_15.v1` -> `.v2`) superseded it "
            "with the PUBLISHED RANGE [+$595.0B, +$673.1B], the two "
            "conventional estimates of 21% -> 15% for all corporations on this "
            "repository's own window, printed side by side in CRFB's "
            "6 September 2024 post. The carried anchor is Tax Foundation's "
            "+$673.1B (this row's `table`), chosen because it is a standalone "
            "analysis of this one reform where PWBM's is a stacked row inside "
            "a whole-campaign package; the figure transcribed here is PWBM's "
            "+$595.0B, the range's other bound, so the spread stays visible. "
            "The module's constant was NOT retuned to the new figure and the "
            "row stays `calibrated_to_target=False`, where PR #119 put it."
        ),
        alternatives=(
            "PWBM, 'The 2024 Trump Campaign Policy Proposals' (26 August "
            "2024) Table 1, 'Lower the corporate income tax rate to 15%': "
            "-$595B conventional over FY2025-2034.",
            "Tax Foundation, same Table 2: -$459.5B dynamic. PWBM publishes "
            "no dynamic dollar figure for the line.",
            "CRFB (6 September 2024) prices a DIFFERENT policy — a revived "
            "section 199 domestic-production deduction reaching a 15% "
            "effective rate for manufacturers only — at about $200B over "
            "FY2026-2035. Not a bound of the range.",
        ),
    ),
    BenchmarkSource(
        policy_id="eliminate_estate_tax",
        provenance=LINE_ITEM,
        document=(
            "Tax Foundation, 'Options for Reforming America's Tax Code 3.0: "
            "A Policymaker's Guide to Tax Reform Trade-Offs' (July 2026), "
            "Option 83, 'Eliminate the Estate and Gift Tax'"
        ),
        publisher="Tax Foundation",
        url=(
            "https://taxfoundation.org/tax-reform-guide/option/"
            "eliminate-the-estate-and-gift-tax/"
        ),
        date="2026-07",
        table="Option 83, '10-Year Change in the Deficit, 2027-2036'",
        row="Conventional Primary Deficit Change",
        page="printed p. 105",
        window="CY2027-2036",
        published_10yr_billions=407.2,
        note=(
            "Target revised 2026-09-09 "
            "(target_revisions.eliminate_estate_tax.v2) from +$350B, which "
            "the scenario's own source field admitted was a 'Model "
            "estimate'. 'This option repeals the estate and gift taxes', "
            "scored on the post-P.L. 119-21 baseline ($15M individual / $30M "
            "joint exemption, 40% top rate): +$407.2B conventional primary "
            "deficit, +$489.4B total. SCOPE: the option repeals the gift tax "
            "too, where `create_eliminate_estate_tax` constructs estate "
            "repeal; CRS R48183 p. 16 puts the estate share at about 90% of "
            "the two, so the published figure is the broader. WINDOW stated "
            "rather than adjusted, on biden_corporate_28_fy2022's precedent. "
            "NOT a target and refused for the reason repeal_ptc refuses "
            "publication 51298: CBO's February 2026 baseline (pub. 61882) "
            "Table 4-1 projects estate and gift receipts of $403B over "
            "FY2027-2036, which is a projection of what the tax raises, not "
            "a score of repealing it."
        ),
        alternatives=(
            "CBO/JCT cost estimate for H.R. 1105, Death Tax Repeal Act of "
            "2015 (2 April 2015): 'reduce revenues... by about $269 billion "
            "over the 2015-2025 period' -- a $5.43M-exemption tax, a "
            "materially different instrument.",
            "JCT JCX-46-17 p. 3 row H, -$171.5B, and JCX-54-17 p. 3 row G, "
            "-$150.7B, both FY2018-2027: repeal BUNDLED with the exemption "
            "doubling and a 35% gift rate. The conference agreement "
            "(JCX-67-17) dropped repeal entirely.",
        ),
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
        searched=(
            "Searched 2026-09-09 (lane H9). No published score of EXPANDING "
            "the negotiation program exists. CBO's December 2024 Options "
            "volume contains no drug-negotiation option at all (searched in "
            "full for 'negotiat', 'drug price', 'prescription drug'). The two "
            "nearest published quantities are neither this policy: CBO's "
            "score of the IRA's EXISTING program -- publication PL117-169 "
            "(7 September 2022), Table 1 p. 5, sec. 11001, 'Providing for "
            "Lower Prices for Certain High-Priced Single Source Drugs', "
            "-$98,521M over FY2022-2031, which already absorbs secs. 11002 "
            "and 11003; and the FY2025 Budget's Table S-6 (report p. 143), "
            "-$200,000M over FY2025-2034 for 'Expand Medicare drug "
            "negotiation, extend inflation rebates and out-of-pocket cost "
            "caps to the commercial market, and other steps', a bundle whose "
            "negotiation leg is not separable from two commercial-market "
            "reforms the module does not build. Worth recording precisely: "
            "the phrase 'at least 50 drugs' appears NOWHERE in the FY2025 "
            "Budget -- it comes from the March 2024 State of the Union -- and "
            "H.R. 4895 / H.R. 6166, which would raise the cohort from 20 to "
            "50, have no CBO estimate. So -$500B is an extrapolation from "
            "$237B, which W4_pharma_part_d.md finding 2 established was never "
            "a negotiation score but CBO's total for the whole drug-pricing "
            "title. RETIREMENT IS RECOMMENDED AND NOT APPLIED: owner decision "
            "(4) of planning/HIGH_STAKES_ACCURACY.md is open and "
            "planning/lanes/HSB_h9_provenance.md carries the one-commit edit."
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
        searched=(
            "Searched 2026-09-09 (lane H9). A published score of "
            "international reference pricing DOES exist and prices a "
            "materially narrower instrument on a baseline this repository "
            "cannot use. CBO's letter to Chairman Frank Pallone of 10 "
            "December 2019 (publication 55936) scores Title I of H.R. 3, the "
            "Elijah E. Cummings Lower Drug Costs Now Act -- prices for "
            "SELECTED drugs negotiated so they 'did not exceed 120 percent of "
            "the average in a reference group of six foreign countries' -- at "
            "'about $456 billion over the 2020-2029 period' of direct-"
            "spending reduction (Table 1: -455,927 million) plus $45B of "
            "revenues. Three things stop it being this row's target. SCOPE: "
            "H.R. 3 caps a selected cohort where the module prices a cap "
            "across Medicare drug spending, so the published figure is a "
            "floor on a narrower policy. BASELINE: it is scored against a "
            "PRE-IRA world with no Medicare negotiation authority at all, and "
            "the IRA has since enacted a program CBO scores at -$98.5B, so "
            "adopting the figure would double-count it. WINDOW: FY2020-2029, "
            "and this repository carries no 2019 vintage. The other published "
            "quantities are further away: CMS's Most Favored Nation interim "
            "final rule (85 FR 76180, 27 November 2020) estimates $85.5B of "
            "net Part B savings over a SEVEN-year model period and was "
            "rescinded effective 28 February 2022; and the Council of "
            "Economic Advisers' May 2026 MFN paper's '$529B in domestic "
            "savings in the next 10 years across all markets' is economy-wide "
            "across all payers rather than a federal budget effect (its only "
            "federal-scoped figure is $36.6B of Medicaid savings). So -$100B "
            "is contradicted in both directions: a fifth of CBO's figure for "
            "a NARROWER policy and an eighth of the module's own answer. "
            "RETIREMENT IS RECOMMENDED AND NOT APPLIED: owner decision (4) is "
            "open, and this is the reconstruction tier's single largest "
            "error, so withdrawing it is exactly the move that needs the "
            "owner's signature rather than a lane's."
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
        searched=(
            "Searched 2026-09-09 (lane H9). NO published ten-year estimate of "
            "a carbon tax starting at $50 per metric ton with a 5% annual "
            "escalator exists. Two totals sit near the design and both use a "
            "2% REAL escalator: Treasury's Office of Tax Analysis Working "
            "Paper 115 (January 2017), 'Methodology for Analyzing a Carbon "
            "Tax', p. 10 -- a tax starting at '$49 per metric ton CO2-e on "
            "January 1, 2019 and rising at roughly a 2 percent real rate' "
            "raises '$2,221 billion in net revenue over the 10-year window "
            "from 2019 through 2028' ($1,846B energy-CO2 only; gross $2,962B "
            "before the standard 25% excise offset); and Rhodium Group for "
            "Columbia SIPA's Center on Global Energy Policy (July 2018), "
            "Table 2, report p. 50 -- a '$50/ton' scenario rising 'at an "
            "approximately 2 percent real rate annually' raising "
            "$1,682-1,781 billion of 2016 dollars over 2020-2029. THE "
            "CARRIED -$1,700B FALLS INSIDE THAT RANGE AND THAT IS NOT "
            "EVIDENCE: the window is six years earlier, the units are 2016 "
            "dollars and the escalator is not the module's, so the "
            "coincidence is two offsetting differences rather than "
            "agreement -- which is why it is not adopted even as a range. CRS "
            "R45625 Table 1 (report p. 23) reports annual 2020 figures only, "
            "and its one $50/5% line is a single-year 2040 range "
            "('approximately $250 billion to $475 billion'). No JCT score of "
            "any carbon-fee bill exists: congress.gov records zero CBO cost "
            "estimates for S.1128 (116th), and the '$2.1 / $2.3 trillion' "
            "figures in sponsor press releases carry no window and no JCX "
            "number. CBO's own Option 73 alternative 1 is the one figure on "
            "this repository's window with the module's exact escalator -- "
            "$919.3B over FY2025-2034 for $25/ton rising 5% -- and doubling "
            "it would be constructing a target. Named in "
            "target_revisions.EXAMINED_NOT_REVISED as a retirement candidate: "
            "a target that restates the model's own calibration is not a "
            "benchmark."
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
