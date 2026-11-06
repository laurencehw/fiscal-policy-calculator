"""Lane B5: the sourced GILTI base and the identity that stopped the lane.

``planning/lanes/B5_corporate_anchor_scope.md`` was to add a sourced GILTI piece
to ``biden_corporate_28``. It stopped because net GILTI is already inside SOI
Table 11's "income subject to tax", which the derived corporate rate channel
prices. These tests pin the transcription and the cross-checks the write-up
relies on, so a later edit to either file shows up here.
"""

import pytest

from fiscal_model.corporate import soi_row
from fiscal_model.international import (
    net_gilti_in_taxable_income_lower_bound_billions,
    soi_gilti_base,
)


def test_transcribed_headline_figures():
    data = soi_gilti_base()
    assert data["gilti_inclusion_billions"] == 607.0
    assert data["section_250_gilti_deduction_billions"] == 311.0
    assert data["section_250_fdii_deduction_billions"] == 111.0
    assert data["net_cfc_tested_income_billions"] == 614.0


def test_section_250_deductions_fit_inside_table_11_foreign_deemed_deductions():
    """GILTI + FDII section 250 deductions are 94.6% of Table 11's $446.3B."""
    data = soi_gilti_base()
    sec250 = (
        data["section_250_gilti_deduction_billions"]
        + data["section_250_fdii_deduction_billions"]
    )
    table11 = float(soi_row(2021)["foreign_deemed_deductions_thousands"]) / 1e6
    assert sec250 <= table11
    assert sec250 / table11 == pytest.approx(0.9456, abs=1e-3)


def test_gilti_fits_inside_table_11_foreign_deemed_income():
    data = soi_gilti_base()
    table11 = float(soi_row(2021)["foreign_deemed_income_thousands"]) / 1e6
    assert data["gilti_inclusion_billions"] <= table11


def test_deduction_implies_a_nonnegative_gross_up():
    """A 50% deduction on GILTI + gross-up of at least $622B >= $607B GILTI."""
    data = soi_gilti_base()
    implied = data["section_250_gilti_deduction_billions"] / data[
        "section_250_gilti_deduction_rate"
    ]
    assert implied >= data["gilti_inclusion_billions"]


def test_net_gilti_is_at_least_twelve_percent_of_the_derived_base():
    """$296B of the TY2021 $2,422.1B income subject to tax, at least."""
    net = net_gilti_in_taxable_income_lower_bound_billions()
    assert net == pytest.approx(296.0)
    base = float(soi_row(2021)["income_subject_to_tax_thousands"]) / 1e6
    assert net / base == pytest.approx(0.1222, abs=1e-3)
