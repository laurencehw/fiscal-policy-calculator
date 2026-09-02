#!/usr/bin/env python3
"""
Rebuild the P.L. 119-21 JCT line-item data file.

P.L. 119-21 is the budget-reconciliation law enacted 4 July 2025 (H.R. 1,
119th Congress). This file names it P.L. 119-21 and refers to the estimate
by JCT's own title for it, never by a popular short name.

Source
------
Joint Committee on Taxation, *Estimated Revenue Effects Relative to the Present
Law Baseline of the Tax Provisions in "Title VII - Finance" of the Substitute
Legislation as Passed by the Senate to Provide for Reconciliation of the Fiscal
Year 2025 Budget*, **JCX-35-25**, 1 July 2025.

* Landing page: https://www.jct.gov/publications/2025/jcx-35-25/
* PDF: https://www.jct.gov/getattachment/eb21dc77-6439-4fc3-8f5d-fc23a8c377e0/x-35-25.pdf

**Why JCX-35-25 is the enacted-law estimate.** JCT published no separate "as
enacted" document for the tax title. The House passed the Senate substitute
without amendment, so the Title VII text JCX-35-25 scores *is* the text enacted
as P.L. 119-21 on 4 July 2025. JCX-34-25 scores the same provisions against a
*current policy* baseline (in which the expiring 2017 provisions are assumed to
continue), and JCX-36-25 / JCX-37-25 are distributional analyses. This file uses
JCX-35-25 because the repository's own convention - and CBO's - is a present-law
baseline.

CBO's companion estimate of the same law, *Estimated Budgetary Effects of Public
Law 119-21 ... Relative to CBO's January 2025 Baseline* (21 July 2025,
[publication 61570](https://www.cbo.gov/publication/61570)), puts the net
deficit increase at $3.4 trillion over 2025-2034: a $1.1 trillion decrease in
direct spending against a $4.5 trillion decrease in revenues. That revenue
figure is JCX-35-25's own net total (-$4,474,972 million) plus the health
provisions CBO scored, which is the cross-check this file's ``net_total`` row
exists for.

Baseline the estimate is built on
--------------------------------
Present law as of mid-2025, scored against CBO's **January 2025** baseline
(publication 61172). That is why Phase D replaced the interpolated
``BaselineVintage.CBO_JAN_2025`` with figures transcribed from that report -
see ``fiscal_model/baseline.py``.

Output
------
``fiscal_model/data_files/validation/pl119_21_jct_line_items.csv``

One row per transcribed provision, chapter subtotal, or net total, carrying:

* ``revenue_effect_2025_34_millions`` - JCT's own sign convention, **negative =
  revenue loss**, in millions, exactly as printed.
* ``deficit_effect_10yr_billions`` - this app's convention, **positive =
  increases the deficit**, in billions. It is the negation of the column above,
  divided by 1,000, and is computed by this script rather than typed, so the
  two can never disagree.
* ``pdf_page`` - the page of the JCX-35-25 PDF the row was read from.
* ``mapping_status`` / ``module_path`` - whether the app can build the
  provision, and from what. ``out_of_scope`` rows carry the reason in ``note``
  and are never scored.

Every row carries ``extracted_by``. The rows below are ``manual``: the JCX
table is a fixed-width, multi-line-label layout that no general parser handles
cleanly, so the totals were transcribed by hand.

``--pdf`` then runs :func:`verify_pages` over the PDF's extracted text. It
checks, for each row, that JCT's printed 2025-34 total appears **on the page
the row records**, with thousands separators as JCT prints them, and **with the
sign JCT printed** - a leading minus for a revenue loss, no marker for a
revenue gain, which is this table's whole sign vocabulary. A mistyped digit and
a flipped sign both fail; a magnitude found only on another page fails and says
so. It does **not** check that a figure was read off the right row (two rows on
one page sharing a magnitude and a sign are indistinguishable to a text
search), it does not check the annual columns (only the total is transcribed),
and it does not check the prose - row labels, chapter headings and effective
dates were verified by reading. One transcribed figure is not printed in the
document at all, the subchapter-A sum; it is reported under ``not_printed``
rather than counted as verified, and :func:`check_internal_consistency`
constrains it against the chapter-5 subtotal instead.

Labels
------
``provision`` is JCT's printed row label and ``chapter`` is JCT's printed
chapter heading, both quoted verbatim from JCX-35-25 with footnote markers
dropped. Where a heading carries the bill's own framing, that framing is the
source's, reproduced rather than paraphrased: selectively trimming a heading
would substitute this file's judgement for the document's words. Two rows carry
a label JCT does not print in that form, and both say so in ``note``: the
subchapter-A sum (JCT's printed subchapter heading plus a parenthetical naming
what was summed) and the net total (JCT prints only "NET TOTAL"). Free-text
``note`` fields describe the provision and the app's ability to model it; they
carry no judgement of the policy.

Usage
-----
    python scripts/extract_pl119_21_line_items.py                 # write the CSV
    python scripts/extract_pl119_21_line_items.py --pdf x-35-25.pdf   # + verify
    python scripts/extract_pl119_21_line_items.py --pdf x-35-25.pdf --verify-only

``--pdf`` may be omitted if the PDF sits next to the CSV as ``x-35-25.pdf``.
jct.gov serves a bot challenge to some HTTP clients, so downloading it is a
manual step; without a readable PDF the script writes the CSV and reports that
verification was skipped rather than silently claiming it passed.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OUT_DIR = PROJECT_ROOT / "fiscal_model" / "data_files" / "validation"
LINE_ITEMS_CSV = OUT_DIR / "pl119_21_jct_line_items.csv"

PUBLICATION = (
    "JCT, Estimated Revenue Effects Relative to the Present Law Baseline of the "
    "Tax Provisions in 'Title VII - Finance' of the Substitute Legislation as "
    "Passed by the Senate to Provide for Reconciliation of the Fiscal Year 2025 "
    "Budget, JCX-35-25 (1 July 2025)"
)
PUBLICATION_URL = "https://www.jct.gov/publications/2025/jcx-35-25/"
PDF_URL = (
    "https://www.jct.gov/getattachment/"
    "eb21dc77-6439-4fc3-8f5d-fc23a8c377e0/x-35-25.pdf"
)
CBO_COMPANION_URL = "https://www.cbo.gov/publication/61570"
BASELINE = (
    "Present law, scored against CBO's January 2025 baseline "
    "(publication 61172)"
)


@dataclass(frozen=True)
class LineItem:
    """One transcribed row of the JCX-35-25 table."""

    provision_id: str
    chapter: str
    jct_item: str
    provision: str
    effective: str
    pdf_page: int
    #: JCT's printed 2025-2034 total, in millions, negative = revenue loss.
    revenue_effect_2025_34_millions: int
    mapping_status: str
    module_path: str = ""
    note: str = ""
    extracted_by: str = "manual"
    #: Rows that are subtotals or the net total rather than a provision. They are
    #: transcribed for cross-checking and are never scored.
    is_reference_row: bool = False

    @property
    def deficit_effect_10yr_billions(self) -> float:
        """App convention: positive increases the deficit."""
        return round(-self.revenue_effect_2025_34_millions / 1000.0, 3)


#: JCT's printed chapter headings, quoted verbatim from JCX-35-25 (pages 1-7).
#: They carry the bill's own framing because they are the document's words:
#: trimming a heading down to a neutral gist would replace the source's label
#: with this file's summary of it, which is exactly what a transcription must
#: not do. ``provision`` below follows the same rule at row level.
_CH1 = "Ch.1: Providing Permanent Tax Relief for Middle-Class Families and Workers"
_CH2 = (
    "Ch.2: Delivering on Presidential Priorities to Provide New "
    "Middle-Class Tax Relief"
)
_CH3 = "Ch.3: Establishing Certainty and Competitiveness for American Job Creators"
_CH4 = "Ch.4: Investing in American Families, Communities, and Small Businesses"
_CH5 = (
    "Ch.5: Ending Green New Deal Spending, Promoting America-First Energy "
    "and Other Reforms"
)
_CH6 = "Ch.6: Enhancing Deduction and Income Tax Credit Guardrails, and Other Reforms"

#: The title the net-total row covers. JCT prints it as the table's first
#: heading line.
_TITLE_VII = "Title VII - Finance Committee"

MAPPED = "mapped"
OUT_OF_SCOPE = "out_of_scope"
REFERENCE = "reference"

_TCJA = "fiscal_model.tcja.create_tcja_extension"

#: Every row below was read off the JCX-35-25 table. ``pdf_page`` is the page of
#: the PDF, which matches the "Page N" header printed on each page after the
#: first.
LINE_ITEMS: tuple[LineItem, ...] = (
    # -- Chapter 1: Providing Permanent Tax Relief for Middle-Class Families --
    LineItem(
        provision_id="pl119_21_rate_extension",
        chapter=_CH1,
        jct_item="1",
        provision="Extension and limited enhancement of reduced rates",
        effective="tyba 12/31/25",
        pdf_page=1,
        revenue_effect_2025_34_millions=-2_193_378,
        mapping_status=MAPPED,
        module_path=f"{_TCJA}(extend_rate_cuts=True)",
        note="TCJA rate schedule made permanent. Maps to the module's "
             "Individual Rate Cuts component.",
    ),
    LineItem(
        provision_id="pl119_21_standard_deduction",
        chapter=_CH1,
        jct_item="2",
        provision="Extension and enhancement of increased standard deduction",
        effective="tyba 12/31/24",
        pdf_page=1,
        revenue_effect_2025_34_millions=-1_424_682,
        mapping_status=MAPPED,
        module_path=f"{_TCJA}(extend_standard_deduction=True)",
        note="Maps to the module's Doubled Standard Deduction component.",
    ),
    LineItem(
        provision_id="pl119_21_personal_exemption_termination",
        chapter=_CH1,
        jct_item="3",
        provision=(
            "Termination of deduction for personal exemptions other than "
            "temporary senior deduction"
        ),
        effective="tyba 12/31/24",
        pdf_page=1,
        revenue_effect_2025_34_millions=1_807_074,
        mapping_status=MAPPED,
        module_path=f"{_TCJA}(keep_exemption_elimination=True)",
        note="Revenue raiser. The new temporary senior deduction has no line of "
             "its own in JCX-35-25 - JCT nets it inside this row - so it cannot "
             "be scored separately.",
    ),
    LineItem(
        provision_id="pl119_21_child_tax_credit",
        chapter=_CH1,
        jct_item="4",
        provision="Extension and enhancement of increased child tax credit",
        effective="tyba 12/31/25",
        pdf_page=1,
        revenue_effect_2025_34_millions=-816_846,
        mapping_status=MAPPED,
        module_path=f"{_TCJA}(extend_ctc=True)",
        note="$2,200 credit, indexed. Maps to the module's Child Tax Credit "
             "Expansion component.",
    ),
    LineItem(
        provision_id="pl119_21_qbi_199a",
        chapter=_CH1,
        jct_item="5",
        provision=(
            "Extension and enhancement of deduction for qualified business income"
        ),
        effective="tyba 12/31/25",
        pdf_page=1,
        revenue_effect_2025_34_millions=-736_539,
        mapping_status=MAPPED,
        module_path=f"{_TCJA}(extend_passthrough=True)",
        note="Section 199A. Maps to the module's Pass-Through Deduction component.",
    ),
    LineItem(
        provision_id="pl119_21_estate_gift_exemption",
        chapter=_CH1,
        jct_item="6",
        provision=(
            "Extension and enhancement of increased estate and gift tax "
            "exemption amounts"
        ),
        effective="dda & gma 12/31/25",
        pdf_page=1,
        revenue_effect_2025_34_millions=-211_725,
        mapping_status=MAPPED,
        module_path=f"{_TCJA}(extend_estate=True)",
        note="$15M per decedent from 2026, indexed.",
    ),
    LineItem(
        provision_id="pl119_21_amt_exemption",
        chapter=_CH1,
        jct_item="7",
        provision=(
            "Extension of increased alternative minimum tax exemption amounts, "
            "modification of phaseout thresholds, and increased threshold "
            "phaseout rate"
        ),
        effective="tyba 12/31/25",
        pdf_page=1,
        revenue_effect_2025_34_millions=-1_362_810,
        mapping_status=MAPPED,
        module_path=f"{_TCJA}(extend_amt=True)",
        note="Maps to the module's AMT Exemption Increase component.",
    ),
    LineItem(
        provision_id="pl119_21_mortgage_interest_limitation",
        chapter=_CH1,
        jct_item="8",
        provision=(
            "Extension of limitation on deduction for qualified residence interest"
        ),
        effective="tyba 12/31/25",
        pdf_page=1,
        revenue_effect_2025_34_millions=39_532,
        mapping_status=OUT_OF_SCOPE,
        note="TaxExpenditurePolicy carries a mortgage-interest base, but the "
             "provision extends an existing $750k principal limitation rather "
             "than changing the deduction, and the module has no principal-cap "
             "input.",
    ),
    LineItem(
        provision_id="pl119_21_casualty_loss_limitation",
        chapter=_CH1,
        jct_item="9",
        provision=(
            "Extension and modification of limitation on casualty loss deduction"
        ),
        effective="tyba 12/31/25",
        pdf_page=1,
        revenue_effect_2025_34_millions=1_331,
        mapping_status=OUT_OF_SCOPE,
        note="No casualty-loss base in any module.",
    ),
    LineItem(
        provision_id="pl119_21_misc_itemized_termination",
        chapter=_CH1,
        jct_item="10",
        provision=(
            "Termination of miscellaneous itemized deductions other than "
            "educator expenses"
        ),
        effective="tyba 12/31/25",
        pdf_page=1,
        revenue_effect_2025_34_millions=231_553,
        mapping_status=OUT_OF_SCOPE,
        note="No miscellaneous-itemized-deduction base in any module.",
    ),
    LineItem(
        provision_id="pl119_21_itemized_benefit_limitation",
        chapter=_CH1,
        jct_item="11",
        provision="Limitation on tax benefit of itemized deductions",
        effective="tyba 12/31/25",
        pdf_page=1,
        revenue_effect_2025_34_millions=-255_515,
        mapping_status=OUT_OF_SCOPE,
        note="A 35% cap on the rate at which itemized deductions reduce tax. No "
             "module represents a rate cap on deduction value.",
    ),
    LineItem(
        provision_id="pl119_21_salt_cap_40k",
        chapter=_CH1,
        jct_item="20",
        provision=(
            "Limitation on individual deductions for certain State and local taxes"
        ),
        effective="tyba 12/31/24",
        pdf_page=2,
        revenue_effect_2025_34_millions=946_209,
        mapping_status=MAPPED,
        module_path=f"{_TCJA}(keep_salt_cap=True)",
        note="P.L. 119-21 raises the cap to $40,000 with a phase-down above "
             "$500,000 of income and reverts to $10,000 after 2029. The app's "
             "SALT component represents the flat $10,000 cap only, so this row "
             "is scored against a design the module cannot express - the error "
             "is reported with that stated, not tuned away.",
    ),
    LineItem(
        provision_id="pl119_21_chapter_1_total",
        chapter=_CH1,
        jct_item="Total",
        provision="Total of Chapter 1",
        effective="",
        pdf_page=2,
        revenue_effect_2025_34_millions=-3_963_431,
        mapping_status=REFERENCE,
        is_reference_row=True,
        note="Chapter subtotal, transcribed for cross-checking.",
    ),
    # -- Chapter 2: New Middle-Class Tax Relief --------------------------------
    LineItem(
        provision_id="pl119_21_no_tax_on_tips",
        chapter=_CH2,
        jct_item="1",
        provision="No tax on tips (sunset 12/31/28)",
        effective="tyba 12/31/24",
        pdf_page=2,
        revenue_effect_2025_34_millions=-31_664,
        mapping_status=OUT_OF_SCOPE,
        note="A new above-the-line deduction for qualified tip income. No module "
             "carries a tip-income base.",
    ),
    LineItem(
        provision_id="pl119_21_no_tax_on_overtime",
        chapter=_CH2,
        jct_item="2",
        provision="No tax on overtime (sunset 12/31/28)",
        effective="tyba 12/31/24",
        pdf_page=2,
        revenue_effect_2025_34_millions=-89_573,
        mapping_status=OUT_OF_SCOPE,
        note="A new deduction for qualified overtime compensation. No module "
             "carries an overtime-premium base.",
    ),
    LineItem(
        provision_id="pl119_21_car_loan_interest",
        chapter=_CH2,
        jct_item="3",
        provision="No tax on car loan interest",
        effective="iia 12/31/24",
        pdf_page=2,
        revenue_effect_2025_34_millions=-30_631,
        mapping_status=OUT_OF_SCOPE,
        note="No auto-loan interest base in any module.",
    ),
    LineItem(
        provision_id="pl119_21_trump_accounts",
        chapter=_CH2,
        jct_item="4",
        provision="Trump accounts and contribution pilot program",
        effective="tyba 12/31/25",
        pdf_page=2,
        revenue_effect_2025_34_millions=-15_233,
        mapping_status=OUT_OF_SCOPE,
        note="New tax-preferred accounts with a federal seed contribution. No "
             "module represents them.",
    ),
    LineItem(
        provision_id="pl119_21_chapter_2_total",
        chapter=_CH2,
        jct_item="Total",
        provision="Total of Chapter 2",
        effective="",
        pdf_page=2,
        revenue_effect_2025_34_millions=-167_101,
        mapping_status=REFERENCE,
        is_reference_row=True,
    ),
    # -- Chapter 3: Business and international ---------------------------------
    LineItem(
        provision_id="pl119_21_full_expensing",
        chapter=_CH3,
        jct_item="A.1",
        provision="Full expensing for certain business property",
        effective="paa 1/19/25",
        pdf_page=2,
        revenue_effect_2025_34_millions=-362_650,
        mapping_status=OUT_OF_SCOPE,
        note="Cost recovery. CorporateTaxPolicy models a statutory rate and a "
             "handful of international levers; it has no depreciation schedule.",
    ),
    LineItem(
        provision_id="pl119_21_rd_expensing",
        chapter=_CH3,
        jct_item="A.2",
        provision=(
            "Full expensing of domestic research and experimental expenditures"
        ),
        effective="apoii tyba 12/31/24",
        pdf_page=2,
        revenue_effect_2025_34_millions=-141_463,
        mapping_status=OUT_OF_SCOPE,
        note="Section 174 amortization repeal. No cost-recovery module.",
    ),
    LineItem(
        provision_id="pl119_21_business_interest",
        chapter=_CH3,
        jct_item="A.3",
        provision="Modification of limitation on business interest",
        effective="tyba 12/31/24",
        pdf_page=2,
        revenue_effect_2025_34_millions=-60_511,
        mapping_status=OUT_OF_SCOPE,
        note="Section 163(j) EBITDA basis. No interest-limitation base.",
    ),
    LineItem(
        provision_id="pl119_21_foreign_tax_credit",
        chapter=_CH3,
        jct_item="B.I.1",
        provision="Modifications related to foreign tax credit limitation",
        effective="tyba 12/31/25",
        pdf_page=3,
        revenue_effect_2025_34_millions=-29_730,
        mapping_status=OUT_OF_SCOPE,
        note="No foreign-tax-credit limitation machinery in the international "
             "module.",
    ),
    LineItem(
        provision_id="pl119_21_fdii_cfc_deduction",
        chapter=_CH3,
        jct_item="B.II.1",
        provision=(
            "Modification of deduction for foreign-derived deduction eligible "
            "income and net CFC tested income"
        ),
        effective="tyba 12/31/25",
        pdf_page=3,
        revenue_effect_2025_34_millions=-86_949,
        mapping_status=OUT_OF_SCOPE,
        note="The successor to FDII and GILTI. CorporateTaxPolicy exposes a GILTI "
             "*rate* change and an FDII repeal switch, neither of which is the "
             "deduction-percentage change this provision makes; mapping one onto "
             "the other would be invention, not modelling.",
    ),
    LineItem(
        provision_id="pl119_21_beat",
        chapter=_CH3,
        jct_item="B.III",
        provision=(
            "Extension and modification of base erosion minimum tax amount"
        ),
        effective="tyba 12/31/25",
        pdf_page=3,
        revenue_effect_2025_34_millions=-30_559,
        mapping_status=OUT_OF_SCOPE,
        note="No BEAT base in any module.",
    ),
    LineItem(
        provision_id="pl119_21_chapter_3_total",
        chapter=_CH3,
        jct_item="Total",
        provision="Total of Chapter 3",
        effective="",
        pdf_page=3,
        revenue_effect_2025_34_millions=-919_984,
        mapping_status=REFERENCE,
        is_reference_row=True,
    ),
    # -- Chapter 4 -------------------------------------------------------------
    LineItem(
        provision_id="pl119_21_chapter_4_total",
        chapter=_CH4,
        jct_item="Total",
        provision="Total of Chapter 4",
        effective="",
        pdf_page=5,
        revenue_effect_2025_34_millions=-156_390,
        mapping_status=REFERENCE,
        is_reference_row=True,
        note="Adoption, education, opportunity-zone and small-business "
             "provisions; no individual row is large enough or close enough to "
             "a module to be worth transcribing separately.",
    ),
    # -- Chapter 5: energy -----------------------------------------------------
    LineItem(
        provision_id="pl119_21_clean_electricity_investment_credit",
        chapter=_CH5,
        jct_item="A.13",
        provision=(
            "Termination and restrictions on clean electricity investment credit"
        ),
        effective="generally tyba DOE",
        pdf_page=5,
        revenue_effect_2025_34_millions=165_669,
        mapping_status=OUT_OF_SCOPE,
        note="Largest single energy-credit termination. See the subchapter row "
             "for why the climate module cannot score any of them.",
    ),
    LineItem(
        provision_id="pl119_21_commercial_clean_vehicles_credit",
        chapter=_CH5,
        jct_item="A.3",
        provision="Termination of qualified commercial clean vehicles credit",
        effective="vaa 9/30/25",
        pdf_page=5,
        revenue_effect_2025_34_millions=104_516,
        mapping_status=OUT_OF_SCOPE,
        note="One of the 15 subchapter A terminations; excluded for leakage "
             "with the rest - see the subchapter row.",
    ),
    LineItem(
        provision_id="pl119_21_clean_vehicle_credit",
        chapter=_CH5,
        jct_item="A.2",
        provision="Termination of clean vehicle credit",
        effective="vaa 9/30/25",
        pdf_page=5,
        revenue_effect_2025_34_millions=77_829,
        mapping_status=OUT_OF_SCOPE,
        note="One of the 15 subchapter A terminations; excluded for leakage "
             "with the rest - see the subchapter row.",
    ),
    LineItem(
        provision_id="pl119_21_residential_clean_energy_credit",
        chapter=_CH5,
        jct_item="A.6",
        provision="Termination of residential clean energy credit",
        effective="ema 12/31/25",
        pdf_page=5,
        revenue_effect_2025_34_millions=77_361,
        mapping_status=OUT_OF_SCOPE,
        note="One of the 15 subchapter A terminations; excluded for leakage "
             "with the rest - see the subchapter row.",
    ),
    LineItem(
        provision_id="pl119_21_advanced_manufacturing_credit_phaseout",
        chapter=_CH5,
        jct_item="A.14",
        provision=(
            "Phase-out and restrictions on advanced manufacturing production credit"
        ),
        effective="tyba DOE & cs tyba 12/31/26",
        pdf_page=6,
        revenue_effect_2025_34_millions=49_966,
        mapping_status=OUT_OF_SCOPE,
        note="One of the 15 subchapter A terminations; excluded for leakage "
             "with the rest - see the subchapter row.",
    ),
    LineItem(
        provision_id="pl119_21_energy_credit_terminations",
        chapter=_CH5,
        jct_item="Subchapter A",
        provision=(
            "Termination of Green New Deal Subsidies (subchapter A, all 15 rows)"
        ),
        effective="",
        pdf_page=6,
        revenue_effect_2025_34_millions=542_653,
        mapping_status=OUT_OF_SCOPE,
        is_reference_row=True,
        note="'Termination of Green New Deal Subsidies' is JCT's own "
             "printed subchapter heading (JCX-35-25 p. 5), quoted verbatim; "
             "the parenthetical says what was summed. LEAKAGE, not a missing "
             "feature: the climate module's IRA-repeal annual is documented as "
             "calibrated to reproduce the -$783B IRA-repeal target, so scoring "
             "an energy-credit repeal through it would reproduce a constant "
             "fitted to the same reform. The subchapter has no printed "
             "subtotal, so this figure is the sum of its 15 rows and is the "
             "one transcribed total the PDF check cannot confirm; it is "
             "checked against the chapter total below instead.",
    ),
    LineItem(
        provision_id="pl119_21_chapter_5_total",
        chapter=_CH5,
        jct_item="Total",
        provision="Total of Chapter 5",
        effective="",
        pdf_page=6,
        revenue_effect_2025_34_millions=499_080,
        mapping_status=REFERENCE,
        is_reference_row=True,
        note="Subchapter A terminations (+542,653) plus subchapter B energy "
             "enhancements (-43,573).",
    ),
    # -- Chapter 6 and the net total -------------------------------------------
    LineItem(
        provision_id="pl119_21_chapter_6_total",
        chapter=_CH6,
        jct_item="Total",
        provision="Total of Chapter 6",
        effective="",
        pdf_page=6,
        revenue_effect_2025_34_millions=58_770,
        mapping_status=REFERENCE,
        is_reference_row=True,
    ),
    LineItem(
        provision_id="pl119_21_net_total",
        chapter=_TITLE_VII,
        jct_item="NET TOTAL",
        provision="Net total, all provisions scored in JCX-35-25",
        effective="",
        pdf_page=7,
        revenue_effect_2025_34_millions=-4_474_972,
        mapping_status=REFERENCE,
        is_reference_row=True,
        note="JCT prints only 'NET TOTAL' as this row's label; the text "
             "here says what it is the net of. Cross-checks against CBO "
             "publication 61570, which puts the law's revenue decrease at "
             "$4.5 trillion over 2025-2034.",
    ),
)


CSV_FIELDS = (
    "provision_id",
    "chapter",
    "jct_item",
    "provision",
    "effective",
    "pdf_page",
    "revenue_effect_2025_34_millions",
    "deficit_effect_10yr_billions",
    "mapping_status",
    "module_path",
    "is_reference_row",
    "extracted_by",
    "note",
)

HEADER_COMMENT = f"""\
# Source: {PUBLICATION}
# Landing page: {PUBLICATION_URL}
# PDF: {PDF_URL}
# Baseline: {BASELINE}
# CBO companion estimate of the same law: {CBO_COMPANION_URL}
# Sign conventions: revenue_effect_2025_34_millions follows JCT (negative =
#   revenue loss); deficit_effect_10yr_billions follows this app (positive =
#   increases the deficit) and is computed, not typed. --pdf re-checks every
#   printed total against the page it was read from, sign included.
# Labels: 'provision' is JCT's printed row label and 'chapter' is JCT's printed
#   chapter heading, both verbatim from JCX-35-25 with footnote markers dropped.
#   Where a heading carries the bill's own framing it is quoted, not
#   paraphrased or trimmed. Two rows carry a label JCT does not print in that
#   form and say so in 'note': the subchapter-A sum and the net total. 'note'
#   describes the provision and whether the app can model it; it carries no
#   judgement of the policy.
# JCT published no separate 'as enacted' estimate of the tax title: the House
#   passed the Senate substitute unamended, so JCX-35-25's Title VII text is the
#   text enacted as P.L. 119-21. JCX-34-25 scores the same provisions against a
#   current-policy baseline instead.
# Rebuilt by scripts/extract_pl119_21_line_items.py.
"""


def write_csv(path: Path = LINE_ITEMS_CSV) -> int:
    """Write the transcribed line items, with the provenance header."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(HEADER_COMMENT)
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for item in LINE_ITEMS:
            writer.writerow(
                {
                    "provision_id": item.provision_id,
                    "chapter": item.chapter,
                    "jct_item": item.jct_item,
                    "provision": item.provision,
                    "effective": item.effective,
                    "pdf_page": item.pdf_page,
                    "revenue_effect_2025_34_millions": (
                        item.revenue_effect_2025_34_millions
                    ),
                    "deficit_effect_10yr_billions": (
                        item.deficit_effect_10yr_billions
                    ),
                    "mapping_status": item.mapping_status,
                    "module_path": item.module_path,
                    "is_reference_row": str(item.is_reference_row).lower(),
                    "extracted_by": item.extracted_by,
                    "note": item.note,
                }
            )
    return len(LINE_ITEMS)


#: Characters a PDF text layer may use for JCT's minus sign. JCX-35-25's own
#: text layer uses plain ASCII hyphen-minus (U+002D) and nothing else; the
#: dashes and the true minus sign are accepted as well so that swapping the
#: extractor (PyMuPDF, pdftotext) cannot turn a correctly transcribed negative
#: into a spurious sign mismatch.
_MINUS_CHARS = "-\u2010\u2011\u2012\u2013\u2014\u2015\u2212"

#: Transcribed totals JCT does not print anywhere in the document, so no amount
#: of text searching can confirm them. They are reported separately rather than
#: counted as verified. The subchapter-A figure is the sum of that subchapter's
#: fifteen printed rows; :func:`check_internal_consistency` is what actually
#: constrains it, against the chapter-5 subtotal.
_DERIVED_TOTALS = frozenset({"pl119_21_energy_credit_terminations"})


def _is_negative(text: str, start: int, end: int) -> bool:
    """Is the figure at ``text[start:end]`` printed as a negative?

    JCX-35-25's own text layer attaches the minus to the digits, but another
    extractor can leave a gap (``"- 2,193,378"``) or space out accounting
    parentheses (``"( 2,193,378 )"``), so whitespace between the marker and the
    number is tolerated. Two guards stop that tolerance from inventing
    negatives out of JCT's other uses of the same character:

    * A **detached** dash counts as a sign only when it stands alone. JCT
      writes a zero cell as ``"---"`` and rules columns off with runs of spaced
      dashes, and neither is a sign - so ``"--- 1,639"`` is a zero followed by
      a positive, not a negative. An **adjacent** dash is always a sign, which
      keeps ``"--- -147,679"`` reading correctly.
    * A leading parenthesis counts only when a closing one actually follows the
      digits.
    """
    gap = start - 1
    while gap >= 0 and text[gap].isspace():
        gap -= 1
    if gap < 0:
        return False

    if text[gap] == "(":
        close = end
        while close < len(text) and text[close].isspace():
            close += 1
        return close < len(text) and text[close] == ")"

    if text[gap] not in _MINUS_CHARS:
        return False
    if gap == start - 1:  # attached to the digits: JCT's own convention
        return True

    prior = gap - 1
    while prior >= 0 and text[prior].isspace():
        prior -= 1
    return prior < 0 or text[prior] not in _MINUS_CHARS


def _printed_signs(haystack: str, magnitude: str) -> list[int]:
    """Sign of every printed occurrence of ``magnitude`` in ``haystack``.

    ``magnitude`` is an absolute value formatted the way JCT prints it, with
    thousands separators (``"2,193,378"``). Matches are anchored on digit
    boundaries, so ``"39,532"`` does not match inside ``"1,139,532"``.

    Returns ``-1`` for an occurrence :func:`_is_negative` reads as a loss and
    ``+1`` otherwise. A bare figure really is JCT's convention for a revenue
    gain in this table - the sign is "minus or nothing" - so the absence of a
    marker is itself evidence, not a skipped check.
    """
    pattern = re.compile(r"(?<![\d,])" + re.escape(magnitude) + r"(?![\d,])")
    return [
        -1 if _is_negative(haystack, match.start(), match.end()) else 1
        for match in pattern.finditer(haystack)
    ]


@dataclass
class VerificationReport:
    """Outcome of checking the transcribed totals against the PDF's text.

    Four disjoint buckets, one entry per row checked:

    ``found``
        The figure is printed on the page the row records, with the sign the
        row transcribes.
    ``sign_mismatch``
        The magnitude is printed on that page, but only with the *opposite*
        sign - a revenue loss transcribed as a raiser, or the reverse. This is
        the failure an ``abs()`` comparison cannot see.
    ``missing``
        The magnitude is not printed on that page at all. The message says
        whether it turns up on another page, which would mean the row's
        ``pdf_page`` is wrong rather than its digits.
    ``not_printed``
        The row's total is derived rather than printed, so it is unverifiable
        here by construction. Reported, never silently skipped.
    """

    found: list[str] = field(default_factory=list)
    sign_mismatch: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    not_printed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.sign_mismatch


def verify_pages(
    pages: Sequence[str], items: Sequence[LineItem] = LINE_ITEMS
) -> VerificationReport:
    """Check each transcribed total against the page of PDF text it came from.

    What this verifies
    ------------------
    For every row, that JCT's printed 2025-34 total appears **on the page the
    row records** (``pdf_page``), formatted as JCT formats it, and **carrying
    the sign JCT printed**: a leading minus for a revenue loss, no marker for a
    revenue gain. A transcription that keeps the right digits but flips the
    sign lands in ``sign_mismatch`` and fails the run. Matches are anchored on
    digit boundaries, so a magnitude is never "verified" by a longer number
    that happens to contain it.

    What this does NOT verify
    -------------------------
    * **That a total was read off the right row.** Two rows on one page whose
      totals share a magnitude and a sign are indistinguishable to a text
      search. Only the subtotal cross-checks in
      :func:`check_internal_consistency` constrain that.
    * **The annual columns.** Only the 2025-34 total is transcribed, so only
      the total is checked.
    * **Row labels, chapter headings and effective dates.** Those are prose;
      they are verified by reading against the PDF, not by this function.
    * **Derived totals.** The subchapter-A sum in :data:`_DERIVED_TOTALS` is
      not printed in the document at all, so it is reported under
      ``not_printed`` and constrained by the chapter-5 cross-check instead.

    ``pages`` is one string of extracted text per PDF page, in order.
    """
    # JCT wraps row labels across lines; normalising whitespace keeps a figure
    # from being hidden by the line break in front of it.
    normalised = [re.sub(r"\s+", " ", page) for page in pages]

    report = VerificationReport()
    for item in items:
        if item.provision_id in _DERIVED_TOTALS:
            report.not_printed.append(
                f"{item.provision_id}: derived, not printed in JCX-35-25; "
                "cross-checked against the chapter subtotal instead"
            )
            continue

        value = item.revenue_effect_2025_34_millions
        printed = f"{abs(value):,}"
        expected = -1 if value < 0 else 1
        index = item.pdf_page - 1
        page_text = normalised[index] if 0 <= index < len(normalised) else ""
        signs = _printed_signs(page_text, printed)

        if not signs:
            elsewhere = [
                str(number)
                for number, text in enumerate(normalised, start=1)
                if _printed_signs(text, printed)
            ]
            where = (
                f"; it is printed on page {', '.join(elsewhere)}, so the row's "
                "pdf_page is wrong"
                if elsewhere
                else ", or anywhere else in the document"
            )
            report.missing.append(
                f"{item.provision_id}: {printed} not on PDF page "
                f"{item.pdf_page}{where}"
            )
        elif expected in signs:
            report.found.append(item.provision_id)
        else:
            report.sign_mismatch.append(
                f"{item.provision_id}: transcribed as {value:+,} but JCX-35-25 "
                f"page {item.pdf_page} prints {signs[0] * abs(value):+,}"
            )
    return report


def verify_against_pdf(pdf_path: Path) -> VerificationReport:
    """Extract the PDF page by page and hand the text to :func:`verify_pages`.

    See :func:`verify_pages` for exactly what is and is not checked.
    """
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise SystemExit(
            "pdfplumber is required for --pdf verification: pip install pdfplumber"
        ) from exc

    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return verify_pages(pages)


def check_internal_consistency() -> list[str]:
    """Cross-check the transcribed subtotals against each other."""
    problems: list[str] = []
    by_id = {item.provision_id: item for item in LINE_ITEMS}

    chapter_1 = sum(
        item.revenue_effect_2025_34_millions
        for item in LINE_ITEMS
        if item.chapter == _CH1 and not item.is_reference_row
    )
    stated = by_id["pl119_21_chapter_1_total"].revenue_effect_2025_34_millions
    # The transcribed chapter-1 rows are the eleven largest of twenty, so they
    # cannot sum to the subtotal; assert only that they are the dominant share
    # and have the same sign, which a transposed digit would break.
    if not (0.8 <= chapter_1 / stated <= 1.2):
        problems.append(
            f"chapter 1: transcribed rows sum to {chapter_1:,}, which is not "
            f"within 20% of the stated subtotal {stated:,}"
        )

    energy_a = by_id["pl119_21_energy_credit_terminations"]
    chapter_5 = by_id["pl119_21_chapter_5_total"]
    subchapter_b = (
        chapter_5.revenue_effect_2025_34_millions
        - energy_a.revenue_effect_2025_34_millions
    )
    if not (-60_000 <= subchapter_b <= -30_000):
        problems.append(
            f"chapter 5: subchapter A ({energy_a.revenue_effect_2025_34_millions:,}) "
            f"and the chapter total ({chapter_5.revenue_effect_2025_34_millions:,}) "
            f"imply a subchapter B of {subchapter_b:,}, outside the transcribed "
            "range of about -43,573"
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help="Path to the JCX-35-25 PDF. Defaults to x-35-25.pdf next to the CSV.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify against the PDF without rewriting the CSV.",
    )
    args = parser.parse_args(argv)

    problems = check_internal_consistency()
    for problem in problems:
        print(f"INTERNAL CHECK FAILED: {problem}", file=sys.stderr)

    pdf_path = args.pdf or (OUT_DIR / "x-35-25.pdf")
    verified: VerificationReport | None = None
    if pdf_path.exists():
        verified = verify_against_pdf(pdf_path)
        print(
            f"PDF verification: {len(verified.found)} totals found on their "
            f"recorded page with JCT's printed sign, "
            f"{len(verified.sign_mismatch)} sign mismatches, "
            f"{len(verified.missing)} missing, "
            f"{len(verified.not_printed)} not printed in the document."
        )
        for line in verified.sign_mismatch:
            print(f"  SIGN MISMATCH {line}", file=sys.stderr)
        for line in verified.missing:
            print(f"  MISSING {line}", file=sys.stderr)
        for line in verified.not_printed:
            print(f"  NOT PRINTED (unverifiable here) {line}")
    else:
        print(
            f"PDF verification SKIPPED: {pdf_path} not found. Download it from "
            f"{PDF_URL} and re-run with --pdf to verify the transcription."
        )

    if not args.verify_only:
        n = write_csv()
        print(f"Wrote {n} rows to {LINE_ITEMS_CSV}")

    failed = bool(problems) or (verified is not None and not verified.ok)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
