"""
Tests for the IRS data-year dropdown in the Data & Methodology panel.

The dropdown used to hardcode ``[2022, 2021]`` which hid the 2023 tables
that were committed under ``fiscal_model/data_files/irs_soi/``. The
helper is now data-file-driven so dropping in a new
``table_1_1_<year>.csv`` makes it available automatically.
"""

from __future__ import annotations

from fiscal_model.ui.settings_controller import _available_irs_data_years


def test_available_years_are_sorted_newest_first():
    years = _available_irs_data_years()
    assert years == sorted(years, reverse=True), (
        f"Expected newest-first ordering, got {years}"
    )


def test_available_years_include_2023():
    """2023 IRS SOI was committed; the dropdown must expose it."""
    years = _available_irs_data_years()
    assert 2023 in years, (
        f"Expected 2023 in available years, got {years}. "
        "If table_1_1_2023.csv was removed, update this test."
    )


def test_available_years_contain_at_least_two_vintages():
    """At least two years must be selectable — the app compares vintages."""
    assert len(_available_irs_data_years()) >= 2


def test_available_years_fallback_is_sane(monkeypatch):
    """When the data layer raises, fall back to the historical default."""
    from fiscal_model.ui import settings_controller

    def _boom():
        raise RuntimeError("simulated IO failure")

    class _BrokenIRS:
        def get_data_years_available(self):
            _boom()

    # Swap the loader class so the helper's IRSSOIData call raises.
    import fiscal_model.data.irs_soi as irs_soi

    monkeypatch.setattr(irs_soi, "IRSSOIData", _BrokenIRS)
    # Reload to ensure the helper picks up the monkey-patched class.
    assert settings_controller._available_irs_data_years() == [2022, 2021]
