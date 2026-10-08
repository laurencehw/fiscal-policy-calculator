"""Regression tests for the follow-ups the 2026-08-31 review left open."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


# --- scorer fallback ---------------------------------------------------------


def test_scorer_init_type_error_is_not_swallowed():
    """A TypeError raised inside a scorer that *does* take start_year is a bug.

    The old ``except TypeError`` turned it into the default-window scorer,
    which reports a different decade with no sign anything went wrong.
    """
    from fiscal_model.models.base import build_scorer_for_start_year

    class BrokenScorer:
        def __init__(self, start_year: int = 2025, use_real_data: bool = True):
            raise TypeError("bug inside the scorer")

    with pytest.raises(TypeError, match="bug inside the scorer"):
        build_scorer_for_start_year(BrokenScorer, start_year=2026, use_real_data=False, cache={})


def test_scorer_without_start_year_still_falls_back():
    from fiscal_model.models.base import build_scorer_for_start_year

    class WindowlessScorer:
        def __init__(self, use_real_data: bool = True):
            self.use_real_data = use_real_data

    cache: dict = {}
    scorer = build_scorer_for_start_year(
        WindowlessScorer, start_year=2026, use_real_data=False, cache=cache
    )
    assert isinstance(scorer, WindowlessScorer)
    assert cache[2026] is scorer


# --- distribution tier captions on a cached rerun ----------------------------


def _render_distribution(st, engine_cls):
    from fiscal_model.ui.tabs import distribution_analysis as tab


    tab.render_distribution_tab(
        st_module=st,
        model_available=True,
        policy=SimpleNamespace(rate_change=0.01, start_year=2026),
        distribution_engine_cls=engine_cls,
        income_group_type_cls=SimpleNamespace(QUINTILE=SimpleNamespace(name="QUINTILE")),
        format_distribution_table_fn=lambda *a, **k: None,
        winners_losers_summary_fn=lambda *a, **k: {},
        run_id="run-1",
        use_microsim=True,
    )


def _texts(mock_method) -> str:
    return " ".join(str(c.args[0]) for c in mock_method.call_args_list if c.args)


def test_distribution_tier_caption_survives_a_cached_rerun(monkeypatch):
    from fiscal_model.ui.tabs import distribution_analysis as tab

    monkeypatch.setattr(tab, "_render_calibration_warning", lambda *a, **k: None)
    analysis = SimpleNamespace(engine="microsim", results=[], total_tax_change=0.0)
    engine = MagicMock()
    engine.return_value.analyze_policy.return_value = analysis

    session = _SessionState()
    for _ in range(2):
        st = MagicMock()
        st.session_state = session
        st.columns.side_effect = lambda spec: [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
        st.selectbox.return_value = "Quintiles (5 groups)"
        _render_distribution(st, engine)
        assert "Return-level microsimulation" in _texts(st.info)
        assert "Income concept" in _texts(st.caption)

    # The second run really was served from the cache.
    assert engine.return_value.analyze_policy.call_count == 1


# --- bill tracker read cache -------------------------------------------------


def test_bill_tracker_reads_are_memoized_until_the_file_changes(tmp_path):
    from fiscal_model.ui.tabs import bill_tracker as bt

    db_file = tmp_path / "bills.db"
    db_file.write_bytes(b"x")
    raw = MagicMock()
    raw.get_all_bills.return_value = [{"bill_id": "hr1"}]
    bt.clear_bill_read_cache()
    db = bt._CachedBillReads(raw, str(db_file))

    first = db.get_all_bills(limit=500)
    first[0]["annotated"] = True  # a caller editing its rows must not poison the cache
    second = db.get_all_bills(limit=500)
    assert raw.get_all_bills.call_count == 1
    assert "annotated" not in second[0]

    db_file.write_bytes(b"xy")  # nightly update: size and mtime change
    db.get_all_bills(limit=500)
    assert raw.get_all_bills.call_count == 2

    bt.clear_bill_read_cache()
    db.get_all_bills(limit=500)
    assert raw.get_all_bills.call_count == 3
