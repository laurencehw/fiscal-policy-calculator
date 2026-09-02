"""The PDF check behind the P.L. 119-21 line-item transcription.

The transcription's whole claim to be worth more than a rounded headline figure
is that every total can be traced back to a page of JCX-35-25. The checker that
backs that claim used to compare ``abs()`` of the transcribed total against the
PDF text, so a revenue *loss* entered as a revenue *raiser* passed silently -
the one transcription error that flips a validation result's sign.

These tests run the checker over small synthetic pages, so they need no PDF:
a correct negative, a correct positive, both flipped signs, a mistyped digit,
a right figure on the wrong page, a magnitude embedded in a longer number, and
the derived total that is not printed at all. The real PDF, when it happens to
sit next to the CSV, is exercised by one extra test that skips without it.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.extract_pl119_21_line_items import (  # noqa: E402
    LINE_ITEMS,
    OUT_DIR,
    OUT_OF_SCOPE,
    LineItem,
    VerificationReport,
    _printed_signs,
    check_internal_consistency,
    verify_against_pdf,
    verify_pages,
)


def _item(provision_id: str, total: int, page: int = 1) -> LineItem:
    """A minimal synthetic row: only the total and the page matter here."""
    return LineItem(
        provision_id=provision_id,
        chapter="Ch.1: synthetic",
        jct_item="1",
        provision="Synthetic provision",
        effective="tyba 12/31/25",
        pdf_page=page,
        revenue_effect_2025_34_millions=total,
        mapping_status=OUT_OF_SCOPE,
    )


#: One page of text in JCT's house style: a revenue loss carries a leading
#: minus, a revenue raiser carries no marker at all.
SYNTHETIC_PAGE = (
    "1.Extension of reduced rates ..... tyba 12/31/25 --- -147,679 -2,193,378\n"
    "2.Termination of personal exemptions ..... tyba 12/31/24 110,625 1,807,074\n"
    "3.Something much larger ..... tyba 12/31/25 --- 1,139,532\n"
)


# ── The sign reader ────────────────────────────────────────────────────────


def test_leading_minus_reads_as_negative():
    assert _printed_signs(SYNTHETIC_PAGE, "2,193,378") == [-1]


def test_bare_figure_reads_as_positive():
    assert _printed_signs(SYNTHETIC_PAGE, "1,807,074") == [1]


def test_parenthesised_figure_reads_as_negative():
    """Some JCT tables use accounting parentheses instead of a minus."""
    assert _printed_signs("Total of Chapter 1 (3,963,431)", "3,963,431") == [-1]


def test_unicode_minus_reads_as_negative():
    """A different PDF extractor may emit U+2212 rather than ASCII '-'."""
    assert _printed_signs("Total −3,963,431", "3,963,431") == [-1]


def test_a_minus_detached_from_the_digits_still_reads_as_negative():
    """Another extractor may leave a space between the sign and the number."""
    assert _printed_signs("Total of Chapter 1 - 3,963,431", "3,963,431") == [-1]
    assert _printed_signs("Total −  3,963,431", "3,963,431") == [-1]


def test_spaced_accounting_parentheses_read_as_negative():
    assert _printed_signs("Total ( 3,963,431 )", "3,963,431") == [-1]


def test_an_unclosed_parenthesis_is_not_an_accounting_negative():
    assert _printed_signs("Total (3,963,431 continued", "3,963,431") == [1]


def test_jcts_zero_cell_is_not_a_sign():
    """JCT writes an empty year as '---'. The figure after it is a raiser.

    This is the trap in tolerating a gap between the marker and the digits:
    read naively, every figure following a zero cell becomes a revenue loss.
    """
    assert _printed_signs("tyba 12/31/25 --- 1,639 3,110", "1,639") == [1]
    assert _printed_signs("credit .... DOE - - - - - 231,553", "231,553") == [1]


def test_a_minus_attached_after_a_zero_cell_still_reads_as_negative():
    """The other half of that trap: '--- -147,679' is a genuine loss."""
    assert _printed_signs("tyba 12/31/25 --- -147,679", "147,679") == [-1]


def test_a_minus_belonging_to_the_previous_column_is_not_borrowed():
    """'-9,264 110,625' is a loss then a raiser, not two losses."""
    assert _printed_signs("tyba 12/31/24 -9,264 110,625", "110,625") == [1]


def test_a_magnitude_inside_a_longer_number_is_not_a_match():
    """'39,532' must not be verified by the '39,532' inside '1,139,532'."""
    assert _printed_signs(SYNTHETIC_PAGE, "39,532") == []
    assert _printed_signs("1,139,5320", "1,139,532") == []


# ── The report ─────────────────────────────────────────────────────────────


def test_correctly_transcribed_totals_are_found():
    report = verify_pages(
        [SYNTHETIC_PAGE],
        [_item("loss", -2_193_378), _item("raiser", 1_807_074)],
    )
    assert report.found == ["loss", "raiser"]
    assert report.sign_mismatch == []
    assert report.missing == []
    assert report.ok


def test_a_loss_transcribed_as_a_raiser_is_a_sign_mismatch():
    """The regression this file exists for: ``abs()`` could not see this."""
    report = verify_pages([SYNTHETIC_PAGE], [_item("flipped", 2_193_378)])
    assert report.found == []
    assert report.missing == []
    assert len(report.sign_mismatch) == 1
    assert "flipped" in report.sign_mismatch[0]
    assert "+2,193,378" in report.sign_mismatch[0]
    assert "-2,193,378" in report.sign_mismatch[0]
    assert not report.ok


def test_a_raiser_transcribed_as_a_loss_is_a_sign_mismatch():
    report = verify_pages([SYNTHETIC_PAGE], [_item("flipped", -1_807_074)])
    assert len(report.sign_mismatch) == 1
    assert not report.ok


def test_a_mistyped_digit_is_missing_not_a_sign_mismatch():
    report = verify_pages([SYNTHETIC_PAGE], [_item("typo", -2_193_387)])
    assert report.sign_mismatch == []
    assert len(report.missing) == 1
    assert "2,193,387" in report.missing[0]
    assert not report.ok


def test_a_figure_on_the_wrong_page_is_reported_as_a_page_error():
    report = verify_pages(
        ["Page 1 has nothing.", SYNTHETIC_PAGE],
        [_item("wrong_page", -2_193_378, page=1)],
    )
    assert len(report.missing) == 1
    assert "pdf_page is wrong" in report.missing[0]
    assert "page 2" in report.missing[0]
    assert not report.ok


def test_a_page_reference_past_the_end_of_the_document_fails():
    report = verify_pages([SYNTHETIC_PAGE], [_item("off_the_end", -2_193_378, page=9)])
    assert len(report.missing) == 1
    assert not report.ok


def test_the_derived_subchapter_sum_is_reported_not_silently_skipped():
    """It is not printed in JCX-35-25, so it cannot be checked here - say so."""
    report = verify_pages(
        [SYNTHETIC_PAGE],
        [_item("pl119_21_energy_credit_terminations", 542_653)],
    )
    assert report.found == []
    assert report.missing == []
    assert len(report.not_printed) == 1
    assert "chapter subtotal" in report.not_printed[0]
    # Unverifiable is not the same as failed: the chapter-5 cross-check in
    # check_internal_consistency() is what constrains this figure.
    assert report.ok


def test_ok_is_false_whenever_a_sign_mismatch_is_recorded():
    report = VerificationReport(found=["a"], sign_mismatch=["b: flipped"])
    assert not report.ok


# ── The real transcription ─────────────────────────────────────────────────


def test_every_transcribed_row_is_covered_by_one_bucket():
    """No row may fall out of the report unnoticed, PDF present or not."""
    report = verify_pages([""] * 10)
    counted = (
        len(report.found)
        + len(report.sign_mismatch)
        + len(report.missing)
        + len(report.not_printed)
    )
    assert counted == len(LINE_ITEMS)


def test_transcription_is_internally_consistent():
    assert check_internal_consistency() == []


@pytest.mark.skipif(
    not (OUT_DIR / "x-35-25.pdf").exists(),
    reason="JCX-35-25 PDF is not checked in; download it to run the real check",
)
def test_the_real_pdf_verifies():  # pragma: no cover - needs the PDF
    report = verify_against_pdf(OUT_DIR / "x-35-25.pdf")
    assert report.sign_mismatch == []
    assert report.missing == []
    assert len(report.found) == len(LINE_ITEMS) - len(report.not_printed)


# ── The label standard ─────────────────────────────────────────────────────


def test_the_dataset_names_the_statute_not_a_nickname():
    """P.L. 119-21 and JCT's own title for the estimate, never a short name.

    The House-passed short title did not survive the Senate, and a popular name
    is a characterisation either way. The transcription names the public law.
    """
    csv_text = (OUT_DIR / "pl119_21_jct_line_items.csv").read_text(encoding="utf-8")
    script_text = (
        PROJECT_ROOT / "scripts" / "extract_pl119_21_line_items.py"
    ).read_text(encoding="utf-8")
    for text in (csv_text, script_text):
        assert "Big Beautiful" not in text
        assert "P.L. 119-21" in text


def test_row_labels_carry_no_editorial_gloss():
    """``provision`` is JCT's row label; the two exceptions declare themselves.

    Every row's ``provision`` is transcribed verbatim from JCX-35-25. Two rows
    cannot be - JCT prints the subchapter-A sum only as a subchapter heading,
    and the net total only as "NET TOTAL" - and both say so in ``note`` rather
    than quietly reading as a quotation.
    """
    by_id = {item.provision_id: item for item in LINE_ITEMS}

    subchapter_a = by_id["pl119_21_energy_credit_terminations"]
    # JCX-35-25 p. 5 prints "Subchapter A - Termination of Green New Deal
    # Subsidies". The label is the document's, not this file's.
    assert subchapter_a.provision.startswith(
        "Termination of Green New Deal Subsidies"
    )
    assert "printed subchapter heading" in subchapter_a.note

    net_total = by_id["pl119_21_net_total"]
    assert "NET TOTAL" in net_total.note

    for item in LINE_ITEMS:
        assert item.provision.strip() == item.provision, item.provision_id
        assert item.chapter.startswith(("Ch.", "Title ")), item.provision_id
