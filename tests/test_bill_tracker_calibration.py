"""
Tests for the bill-tracker calibration band integration.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from fiscal_model.ui.confidence_band import reset_confidence_cache
from fiscal_model.ui.tabs.bill_tracker import (
    _dominant_provision_policy_type,
    _render_bill_calibration_band,
)


def test_dominant_picks_highest_confidence_provision():
    auto_score = {
        "policies_json": json.dumps([
            {"policy_type": "income_tax", "confidence": "low"},
            {"policy_type": "corporate_tax", "confidence": "high"},
            {"policy_type": "estate_tax", "confidence": "medium"},
        ]),
    }
    assert _dominant_provision_policy_type(auto_score) == "corporate_tax"


def test_dominant_returns_none_for_empty_or_malformed():
    assert _dominant_provision_policy_type({}) is None
    assert _dominant_provision_policy_type({"policies_json": ""}) is None
    assert _dominant_provision_policy_type({"policies_json": "{not valid"}) is None
    assert _dominant_provision_policy_type({"policies_json": "[]"}) is None


def test_dominant_handles_unranked_confidence():
    """Provisions without a confidence label still resolve to *some* type."""
    auto_score = {
        "policies_json": json.dumps([
            {"policy_type": "estate_tax"},
            {"policy_type": "income_tax"},
        ]),
    }
    # `max` with all-equal keys returns the first element.
    assert _dominant_provision_policy_type(auto_score) == "estate_tax"


def test_render_bill_calibration_band_emits_caption_for_known_type():
    """The band is the Tier 1 corporate class, not a category mean.

    Lane R3 took that class from one row to four — CBO prices an identical
    21%-to-22% increase in all four *Options* volumes — so the band is now the
    mean and worst of four pre-registered rows, with the count said out loud. The
    assertion that matters is unchanged: the band names its own sample size, so
    a reader can see how thin it is.
    """
    reset_confidence_cache()
    st = MagicMock()
    auto_score = {
        "policies_json": json.dumps([
            {"policy_type": "corporate_tax", "confidence": "high"},
        ]),
    }
    _render_bill_calibration_band(st, auto_score, total_billions=-1347.0)

    assert st.caption.called
    caption_text = st.caption.call_args[0][0]
    assert "Out-of-sample band" in caption_text
    assert "corporate" in caption_text
    assert "4 pre-registered corporate rows" in caption_text
    assert "demo-grade" in caption_text
    # The claim that H4 removed must not come back by another route.
    assert "calibrated run" not in caption_text


def test_render_bill_calibration_band_is_silent_for_a_type_with_no_tier1_row():
    """Most extracted types have no out-of-sample row, and get no band.

    An estate provision used to draw the ``Estate`` category's 4.7% — a mean
    over three fitted rows whose agreement is bookkeeping. Nothing measures this
    model's accuracy on an estate reform, so nothing is printed.
    """
    reset_confidence_cache()
    st = MagicMock()
    auto_score = {
        "policies_json": json.dumps([
            {"policy_type": "estate_tax", "confidence": "high"},
        ]),
    }
    _render_bill_calibration_band(st, auto_score, total_billions=-450.0)
    assert not st.caption.called


def test_render_bill_calibration_band_silent_when_no_provisions():
    """Bills without parsed provisions should not crash or emit a band."""
    reset_confidence_cache()
    st = MagicMock()
    _render_bill_calibration_band(st, {}, total_billions=100.0)
    assert not st.caption.called


def test_render_bill_calibration_band_silent_on_compute_failure(monkeypatch):
    """A scorecard failure must produce no band rather than a 500."""
    from fiscal_model.validation import credibility as cb_module

    def _boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(cb_module, "tier1_class_bands", _boom)
    reset_confidence_cache()

    st = MagicMock()
    auto_score = {"policies_json": json.dumps([{"policy_type": "corporate_tax"}])}
    _render_bill_calibration_band(st, auto_score, total_billions=-1347.0)
    assert not st.caption.called
